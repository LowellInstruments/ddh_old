import asyncio
import datetime
import os

from dds.csv_data import file_lowell_raw_csv_to_emolt_lt_csv
from dds.lef import dds_create_file_lef
from mat.ble.ble_mat_utils import (
    ble_mat_crc_local_vs_remote,
    DDH_GUI_UDP_PORT, ble_mat_disconnect_all_devices_ll,
)
from mat.ble.bleak.cc26x2r import BleCC26X2
from dds.ble_utils_dds import ble_logger_ccx26x2r_needs_a_reset
from mat.lix import convert_lix_file
from mat.utils import linux_is_rpi
from utils.ddh_config import ddh_get_cfg_gear_type
from utils.ddh_shared import (
    send_ddh_udp_gui as _u,
    STATE_DDS_BLE_LOW_BATTERY,
    STATE_DDS_BLE_RUN_STATUS, STATE_DDS_BLE_ERROR_RUN,
    STATE_DDS_BLE_DOWNLOAD_ERROR_TP_SENSOR,
    BLEAppException, ael, get_ddh_rerun_flag,
)
from utils.logs import lg_dds as lg
from utils.ddh_shared import (
    get_dl_folder_path_from_mac,
    create_folder_logger_by_mac,
)


def _une(rv, notes, e):
    # une: update notes error
    if not rv:
        return
    notes["error"] = "error " + str(e)


def _rae(rv, s):
    if rv:
        raise BLEAppException("TDO interact " + s)


class BleTDODownload:
    @staticmethod
    async def download_recipe(lc, mac, info, g, notes):

        # initialize variables
        notes["battery_level"] = 0xFFFF
        notes["error"] = ""
        rerun_flag = get_ddh_rerun_flag()
        create_folder_logger_by_mac(mac)
        dl_files = []

        rv = await lc.connect(mac)
        _une(rv, notes, "comm.")
        _rae(rv, "connecting")
        lg.a("connected to {}".format(mac))

        if ble_logger_ccx26x2r_needs_a_reset(mac):
            await lc.cmd_rst()
            # out of here for sure
            raise BLEAppException("TDO interact logger reset file")

        rv = await lc.cmd_sws(g)
        _rae(rv, "sws")
        lg.a("SWS | OK")

        rv = await lc.cmd_wak("off")
        _rae(rv, "wak")
        lg.a("WAK | off OK")

        rv, t = await lc.cmd_utm()
        _rae(rv, "utm")
        lg.a("UTM | {}".format(t))

        rv, b = await lc.cmd_bat()
        _rae(rv, "bat")
        lg.a("BAT | {} mV".format(b))
        notes["battery_level"] = b
        if b < 982:
            # give time to GUI to display
            _u("{}/{}".format(STATE_DDS_BLE_LOW_BATTERY, mac))
            await asyncio.sleep(3)

        rv, v = await lc.cmd_gfv()
        _rae(rv, "gfv")
        lg.a("GFV | {}".format(v))

        rv, v = await lc.cmd_gtm()
        _rae(rv, "gtm")
        lg.a("GTM | {}".format(v))

        rv = await lc.cmd_stm()
        _rae(rv, "stm")
        lg.a("STM | OK")

        # disable log for lower power consumption
        rv, v = await lc.cmd_log()
        _rae(rv, "log")
        if linux_is_rpi():
            if v != 0:
                rv, v = await lc.cmd_log()
                _rae(rv, "log")
        else:
            # we want logs while developing
            if v != 1:
                rv, v = await lc.cmd_log()
                _rae(rv, "log")

        rv, ls = await lc.cmd_dir()
        _rae(rv, "dir error " + str(rv))
        lg.a("DIR | {}".format(ls))

        # iterate files present in logger
        for name, size in ls.items():

            # delete zero-bytes files
            if size == 0:
                rv = await lc.cmd_del(name)
                _rae(rv, "del")
                continue

            # download file
            lg.a("downloading file {}".format(name))
            rv = await lc.cmd_dwg(name)
            _rae(rv, "dwg")
            up = DDH_GUI_UDP_PORT
            rv, d = await lc.cmd_dwl(int(size), ip="127.0.0.1", port=up)
            _rae(rv, "dwl")
            file_data = lc.ans

            # calculate crc
            path = "/tmp/ddh_crc_file"
            with open(path, "wb") as f:
                f.write(lc.ans)
            rv, r_crc = await lc.cmd_crc(name)
            _rae(rv, "crc")
            rv, l_crc = ble_mat_crc_local_vs_remote(path, r_crc)
            if (not rv) and os.path.exists(path):
                e = "error: bad CRC so removing local file {}"
                lg.a(e.format(path))
                os.unlink(path)

            # save file in our local disk
            path = str(get_dl_folder_path_from_mac(mac) / name)
            with open(path, "wb") as f:
                f.write(file_data)
            lg.a("downloaded file {}".format(name))

            # add to the output list
            dl_files.append(path)

            # delete file in logger
            rv = await lc.cmd_del(name)
            _rae(rv, "del")
            lg.a("deleted file {}".format(name))

            # create LEF file with download info
            lg.a("creating file LEF for {}".format(name))
            dds_create_file_lef(g, name)

        # format file-system
        rv = await lc.cmd_frm()
        _rae(rv, "frm")
        lg.a("FRM | OK")

        # check sensors measurement, Temperature
        rv = await lc.cmd_gst()
        # rv: (0, 46741)
        bad_rv = not rv or rv[0] == 1 or rv[1] == 0xFFFF or rv[1] == 0
        if bad_rv:
            _une(bad_rv, notes, "T_sensor_error")
            lg.a('GST | error {}'.format(rv))
            _u(STATE_DDS_BLE_DOWNLOAD_ERROR_TP_SENSOR)
            await asyncio.sleep(5)
        _rae(bad_rv, "gst")

        # check sensors measurement, Pressure
        rv = await lc.cmd_gsp()
        # rv: (0, 1241)
        bad_rv = not rv or rv[0] == 1 or rv[1] == 0xFFFF or rv[1] == 0
        if bad_rv:
            _une(bad_rv, notes, "P_sensor_error")
            lg.a('GSP | error {}'.format(rv))
            _u(STATE_DDS_BLE_DOWNLOAD_ERROR_TP_SENSOR)
            await asyncio.sleep(5)
        _rae(bad_rv, "gsp")

        # wake mode
        if rerun_flag:
            rv = await lc.cmd_wak("on")
        else:
            rv = await lc.cmd_wak("off")
        _rae(rv, "wak")
        lg.a("WAK | OK")
        await asyncio.sleep(1)

        if rerun_flag:
            rv = await lc.cmd_rws(g)
            if rv:
                _u(STATE_DDS_BLE_ERROR_RUN)
                await asyncio.sleep(5)
            _rae(rv, "rws")
            lg.a("RWS | OK")
        else:
            # GUI telling this
            _u("{}/{}".format(STATE_DDS_BLE_RUN_STATUS, "off"))
            # give time to GUI to display
            await asyncio.sleep(5)

        # -----------------------
        # bye, bye to this logger
        # -----------------------
        await lc.disconnect()

        return 0, dl_files


async def ble_interact_tdo(mac, info, g, h):

    notes = {}
    lc = BleCC26X2(h)

    try:
        # -------------------------
        # BLE connection done here
        # -------------------------
        lg.a(f"interacting TDO logger, info {info}")
        rv, dl_files = await BleTDODownload.download_recipe(lc, mac, info, g, notes)

        # convert lix files
        lix_f = [f for f in dl_files if f.endswith(".lix")]
        for f in lix_f:
            rv_cnv = convert_lix_file(f)
            if rv_cnv == 0:
                if ddh_get_cfg_gear_type() != 0:
                    file_lowell_raw_csv_to_emolt_lt_csv(f)
            else:
                lg.a(f'error: DDH converting TDO file {f}')

    except Exception as ex:
        lg.a("error dl_tdo_exception {}".format(ex))
        rv = 1

    finally:
        return rv, notes


# ------
# test
# ------
if __name__ == "__main__":
    ble_mat_disconnect_all_devices_ll()
    # we currently in 'ddh/dds'
    os.chdir('..')
    _m = "D0:2E:AB:D9:29:48"
    _i = "TAP1"
    _g = ("+1.111111", "-2.222222", datetime.datetime.now(), 0)
    _h = "hci0"
    _args = [_m, _i, _g, _h]
    ael.run_until_complete(ble_interact_tdo(*_args))
