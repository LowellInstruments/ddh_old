import asyncio
import datetime
import os

from dds.csv_data import file_lowell_raw_csv_to_emolt_lt_csv
from dds.lef import dds_create_file_lef
from dds.notifications import notify_logger_error_sensor_pressure, notify_logger_error_low_battery, LoggerNotification
from mat.ble.ble_mat_utils import (
    ble_mat_crc_local_vs_remote,
    DDH_GUI_UDP_PORT, ble_mat_disconnect_all_devices_ll,
)
from mat.ble.bleak.cc26x2r import BleCC26X2
from dds.ble_utils_dds import ble_logger_ccx26x2r_needs_a_reset, dds_ble_init_rv_notes
from mat.lix import convert_lix_file
from mat.utils import linux_is_rpi
from utils.ddh_config import (ddh_get_cfg_gear_type, dds_get_cfg_logger_sn_from_mac,
                              dds_get_cfg_flag_download_test_mode)
from utils.ddh_shared import (
    send_ddh_udp_gui as _u,
    STATE_DDS_BLE_RUN_STATUS, STATE_DDS_BLE_ERROR_RUN,
    STATE_DDS_BLE_DOWNLOAD_ERROR_TP_SENSOR,
    BLEAppException, ael, get_ddh_rerun_flag_li, TESTMODE_FILENAMEPREFIX
)
from utils.logs import lg_dds as lg
from utils.ddh_shared import (
    get_dl_folder_path_from_mac,
    create_folder_logger_by_mac,
)


def _une(rv, notes, e, ce=0):
    # une: update notes error
    if not rv:
        return
    notes["error"] = "error " + str(e)
    notes["crit_error"] = int(ce)


def _rae(rv, s):
    if rv:
        raise BLEAppException("TDO interact " + s)


class BleTDODownload:
    @staticmethod
    async def download_recipe(lc, mac, g, notes: dict):

        dds_ble_init_rv_notes(notes)
        rerun_flag = get_ddh_rerun_flag_li()
        create_folder_logger_by_mac(mac)
        sn = dds_get_cfg_logger_sn_from_mac(mac)

        rv = await lc.connect(mac)
        _une(rv, notes, "comm.")
        _rae(rv, "connecting")
        lg.a("connected to {}".format(mac))

        if ble_logger_ccx26x2r_needs_a_reset(mac):
            await lc.cmd_rst()
            # out of here for sure
            raise BLEAppException("TDO interact logger reset file")

        rv, state = await lc.cmd_sts()
        _rae(rv, "sts")
        lg.a(f"STS | logger was {state}")

        rv = await lc.cmd_sws(g)
        _rae(rv, "sws")
        lg.a("SWS | OK")

        rv, t = await lc.cmd_utm()
        _rae(rv, "utm")
        lg.a("UTM | {}".format(t))

        rv, b = await lc.cmd_bat()
        _rae(rv, "bat")
        lg.a("BAT | {} mV".format(b))
        notes["battery_level"] = b
        if b < 982:
            ln = LoggerNotification(mac, sn, 'TDO', b)
            notify_logger_error_low_battery(g, ln)
            _u("f{STATE_DDS_BLE_LOW_BATTERY}/{mac}")
            # give time to GUI to display
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
            if dds_get_cfg_flag_download_test_mode():
                name = TESTMODE_FILENAMEPREFIX + name
            path = str(get_dl_folder_path_from_mac(mac) / name)
            with open(path, "wb") as f:
                f.write(file_data)
            lg.a("downloaded file {}".format(name))

            # add to the output list
            notes['dl_files'].append(path)

            # delete file in logger
            rv = await lc.cmd_del(name)
            _rae(rv, "del")
            lg.a("deleted file {}".format(name))

            # create LEF file with download info
            lg.a("creating file LEF for {}".format(name))
            dds_create_file_lef(g, name)

        # format file-system
        await asyncio.sleep(.1)
        rv = await lc.cmd_frm()
        _rae(rv, "frm")
        lg.a("FRM | OK")

        # check sensors measurement, Temperature
        rv = await lc.cmd_gst()
        # rv: (0, 46741)
        bad_rv = not rv or rv[0] == 1 or rv[1] == 0xFFFF or rv[1] == 0
        if bad_rv:
            _une(bad_rv, notes, "T_sensor_error", ce=1)
            lg.a('GST | error {}'.format(rv))
            _u(STATE_DDS_BLE_DOWNLOAD_ERROR_TP_SENSOR)
            await asyncio.sleep(5)
        _rae(bad_rv, "gst")

        # check sensors measurement, Pressure
        rv = await lc.cmd_gsp()
        # rv: (0, 1241)
        bad_rv = not rv or rv[0] == 1 or rv[1] == 0xFFFF or rv[1] == 0
        if bad_rv:
            _une(bad_rv, notes, "P_sensor_error", ce=1)
            lg.a('GSP | error {}'.format(rv))
            ln = LoggerNotification(mac, sn, 'TDO', b)
            notify_logger_error_sensor_pressure(g, ln)
            _u(STATE_DDS_BLE_DOWNLOAD_ERROR_TP_SENSOR)
            await asyncio.sleep(5)
        _rae(bad_rv, "gsp")

        # wake mode
        w = "on" if rerun_flag else "off"
        rv = await lc.cmd_wak(w)
        _rae(rv, "wak")
        lg.a(f"WAK | {w} OK")
        await asyncio.sleep(1)

        if rerun_flag:
            rv = await lc.cmd_rws(g)
            if rv:
                _u(STATE_DDS_BLE_ERROR_RUN)
                await asyncio.sleep(5)
            _rae(rv, "rws")
            lg.a("RWS | OK")
            notes['rerun'] = True
        else:
            # GUI telling this
            notes['rerun'] = False
            lg.a("warning: telling this logger is not set for auto-re-run")
            _u(f"{STATE_DDS_BLE_RUN_STATUS}/off")
            # give time to GUI to display
            await asyncio.sleep(5)

        # -----------------------
        # bye, bye to this logger
        # -----------------------
        await lc.disconnect()
        return 0


async def ble_interact_tdo(mac, info, g, h):

    rv = 0
    notes = {}
    lc = BleCC26X2(h)

    try:
        # -------------------------
        # BLE connection done here
        # -------------------------
        lg.a(f"interacting TDO logger, info {info}")
        rv = await BleTDODownload.download_recipe(lc, mac, g, notes)

    except Exception as ex:
        await lc.disconnect()
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
    _i = "TDO"
    _g = ("+1.111111", "-2.222222", datetime.datetime.now(), 0)
    _h = "hci0"
    _args = [_m, _i, _g, _h]
    ael.run_until_complete(ble_interact_tdo(*_args))
