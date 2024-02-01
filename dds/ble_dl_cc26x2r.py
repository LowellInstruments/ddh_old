import asyncio
import datetime
import os
from dds.lef import dds_create_file_lef
from dds.sqs import sqs_msg_logger_error_oxygen_zeros
from mat.ble.ble_mat_utils import (
    ble_mat_crc_local_vs_remote,
    DDH_GUI_UDP_PORT, ble_mat_disconnect_all_devices_ll,
)
from mat.ble.bleak.cc26x2r import BleCC26X2
from mat.ble.bleak.cc26x2r_sim import BleCC26X2Sim, ble_logger_is_cc26x2r_simulated
from dds.ble_utils_dds import ble_logger_ccx26x2r_needs_a_reset
from utils.ddh_config import dds_get_cfg_logger_sn_from_mac
from utils.ddh_shared import (
    send_ddh_udp_gui as _u,
    STATE_DDS_BLE_LOW_BATTERY,
    STATE_DDS_BLE_RUN_STATUS, STATE_DDS_BLE_DOWNLOAD_ERROR_GDO, STATE_DDS_BLE_ERROR_RUN, BLEAppException, ael,
    get_ddh_rerun_flag,
)
from utils.logs import lg_dds as lg
from utils.ddh_shared import (
    get_dl_folder_path_from_mac,
    create_folder_logger_by_mac,
)
import json


MC_FILE = "MAT.cfg"


def _une(rv, notes, e):
    # une: update notes error
    if not rv:
        return
    notes["error"] = "error " + str(e)


def _rae(rv, s):
    if rv:
        raise BLEAppException("cc26x2 interact " + s)


class BleCC26X2Download:
    @staticmethod
    async def download_recipe(lc, mac, info, g, notes: dict):

        # initialize variables
        notes["battery_level"] = 0xFFFF
        notes["error"] = ""
        simulation = ble_logger_is_cc26x2r_simulated(mac)
        rerun_flag = get_ddh_rerun_flag()
        create_folder_logger_by_mac(mac)
        _is_a_lix_logger = False

        rv = await lc.connect(mac)
        _une(rv, notes, "comm.")
        _rae(rv, "connecting")
        lg.a("connected to {}".format(mac))

        if ble_logger_ccx26x2r_needs_a_reset(mac):
            await lc.cmd_rst()
            # out of here for sure
            raise BLEAppException("cc26x2 interact logger reset file")

        # to know if this DO-X logger uses LID or LIX files
        rv = await lc.cmd_xod(g)
        _is_a_lix_logger = rv == 0
        lg.a(f"XOD | LIX = {_is_a_lix_logger}")

        # STOP with STRING
        rv = await lc.cmd_sws(g)
        _rae(rv, "sws")
        lg.a("SWS | OK")

        rv, t = await lc.cmd_utm()
        _rae(rv, "utm")
        lg.a("UTM | {}".format(t))

        # checking battery level for DO-x loggers
        rv, b = await lc.cmd_bat()
        _rae(rv, "bat")
        lg.a("BAT | {} mV".format(b))
        notes["battery_level"] = b
        if b < 1500:
            # give time to GUI to display
            _u("{}/{}".format(STATE_DDS_BLE_LOW_BATTERY, mac))
            await asyncio.sleep(5)

        rv, v = await lc.cmd_gfv()
        _rae(rv, "gfv")
        lg.a("GFV | {}".format(v))

        rv, v = await lc.cmd_gtm()
        _rae(rv, "gtm")
        lg.a("GTM | {}".format(v))

        rv = await lc.cmd_stm()
        _rae(rv, "stm")
        lg.a("STM | OK")

        rv, ls = await lc.cmd_dir()
        _rae(rv, "dir error " + str(rv))
        lg.a("DIR | {}".format(ls))
        if MC_FILE not in ls.keys():
            _rae(rv, "fex error: no configuration file in logger")

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
            if not simulation:
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

            # no-deleting the logger configuration file
            if name == MC_FILE:
                continue

            # delete file in logger
            rv = await lc.cmd_del(name)
            _rae(rv, "del")
            lg.a("deleted file {}".format(name))

            # create LEF file with download info
            lg.a("creating file LEF for {}".format(name))
            dds_create_file_lef(g, name)

        # format file-system, o/w DO-1 loggers (NAND mem) get slower
        rv = await lc.cmd_frm()
        _rae(rv, "frm")
        lg.a("FRM | OK")

        # restore the logger config file
        path = str(get_dl_folder_path_from_mac(mac) / MC_FILE)
        if not simulation:
            with open(path) as f:
                j = json.load(f)
                rv = await lc.cmd_cfg(j)
                _rae(rv, "cfg")
                lg.a("CFG | OK")

        # see if the DO sensor works
        if "DO-" in info:
            rv = await lc.cmd_gdo()
            bad_rv = not rv or (rv and rv[0] == "0000")
            if bad_rv:
                lg.a("GDO | error {}".format(rv))
                _u(STATE_DDS_BLE_DOWNLOAD_ERROR_GDO)
                _une(bad_rv, notes, "ox_sensor_error")
                if rv and rv[0] == "0000":
                    sn = dds_get_cfg_logger_sn_from_mac(mac)
                    lat, lon, _, __ = g
                    sqs_msg_logger_error_oxygen_zeros(mac,
                                                      sn,
                                                      lat, lon)
                await asyncio.sleep(5)
            _rae(bad_rv, "gdo")
            lg.a("GDO | {}".format(rv))

        # wake mode
        if rerun_flag:
            rv = await lc.cmd_wak("on")
        else:
            rv = await lc.cmd_wak("off")

        _rae(rv, "wak")
        lg.a("WAK | OK")

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

        return 0


async def ble_interact_cc26x2(mac, info, g, h):

    notes = {}
    if ble_logger_is_cc26x2r_simulated(mac):
        lc = BleCC26X2Sim()
    else:
        lc = BleCC26X2(h)

    try:
        # -------------------------
        # BLE connection done here
        # -------------------------
        s = "interacting with CC26X2 logger, info {}"
        lg.a(s.format(info))
        rv = await BleCC26X2Download.download_recipe(lc, mac, info, g, notes)

    except Exception as ex:
        lg.a("error dl_cc26x2r_exception {}".format(ex))
        rv = 1

    finally:
        return rv, notes


# ------
# test
# ------
if __name__ == "__main__":
    # we currently in 'ddh/dds'
    ble_mat_disconnect_all_devices_ll()
    os.chdir('..')
    _m = "11:22:33:44:55:66"
    # do not use this one for TAP loggers but 'ble_dl_tap.py'
    _i = "DO-1"
    _g = ("+1.111111", "-2.222222", datetime.datetime.now(), 0)
    _h = "hci0"
    _args = [_m, _i, _g, _h]
    ael.run_until_complete(ble_interact_cc26x2(*_args))
