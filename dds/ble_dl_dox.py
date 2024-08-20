import asyncio
import datetime
import os

from dds.gpq import dds_create_file_fixed_gpq
from dds.lef import dds_create_file_lef
from dds.notifications import notify_logger_error_sensor_oxygen, notify_logger_error_low_battery, LoggerNotification
from mat.ble.ble_mat_utils import (
    ble_mat_crc_local_vs_remote,
    DDH_GUI_UDP_PORT, ble_mat_disconnect_all_devices_ll,
)
from mat.ble.bleak.cc26x2r import BleCC26X2
from dds.ble_utils_dds import ble_logger_ccx26x2r_needs_a_reset, dds_ble_init_rv_notes
from utils.ddh_config import dds_get_cfg_logger_sn_from_mac, dds_get_cfg_flag_download_test_mode, ddh_get_cfg_gear_type
from utils.ddh_shared import (
    send_ddh_udp_gui as _u,
    STATE_DDS_BLE_LOW_BATTERY,
    STATE_DDS_BLE_RUN_STATUS, STATE_DDS_BLE_DOWNLOAD_ERROR_GDO,
    STATE_DDS_BLE_ERROR_RUN, BLEAppException, ael, get_ddh_rerun_flag_li, TESTMODE_FILENAMEPREFIX,
)
from utils.logs import lg_dds as lg
from utils.ddh_shared import (
    get_dl_folder_path_from_mac,
    create_folder_logger_by_mac,
)
import json


MC_FILE = "MAT.cfg"


def _une(rv, notes, e, ce=0):
    # une: update notes error
    if not rv:
        return
    notes["error"] = "error " + str(e)
    notes["crit_error"] = int(ce)


def _rae(rv, s):
    if rv:
        raise BLEAppException("cc26x2 interact " + s)


class BleCC26X2Download:
    @staticmethod
    async def download_recipe(lc, mac, g, notes: dict, u):

        dds_ble_init_rv_notes(notes)
        rerun_flag = get_ddh_rerun_flag_li()
        create_folder_logger_by_mac(mac)
        _is_a_lid_v2_logger = False
        sn = dds_get_cfg_logger_sn_from_mac(mac)

        rv = await lc.connect(mac)
        _une(rv, notes, "comm.")
        _rae(rv, "connecting")
        lg.a(f"connected to {mac}")

        if ble_logger_ccx26x2r_needs_a_reset(mac):
            await lc.cmd_rst()
            # out of here for sure
            raise BLEAppException("cc26x2 interact logger reset file")

        # to know if this DO-X logger uses LID or LIX files
        rv = await lc.cmd_xod()
        _is_a_lid_v2_logger = rv == 0
        lg.a(f"XOD | LIX {_is_a_lid_v2_logger}")

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
            ln = LoggerNotification(mac, sn, 'DOX', b)
            ln.uuid_interaction = u
            notify_logger_error_low_battery(g, ln)
            _u(f"{STATE_DDS_BLE_LOW_BATTERY}/{mac}")
            # give time to GUI to display
            await asyncio.sleep(5)

        rv, v = await lc.cmd_gfv()
        _rae(rv, "gfv")
        lg.a("GFV | {}".format(v))
        notes['gfv'] = v

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
            del_name = name
            if dds_get_cfg_flag_download_test_mode() and name != MC_FILE:
                name = TESTMODE_FILENAMEPREFIX + name
            path = str(get_dl_folder_path_from_mac(mac) / name)
            with open(path, "wb") as f:
                f.write(file_data)
            lg.a(f"OK: downloaded file {name}")

            # no-deleting the logger configuration file
            if name == MC_FILE:
                continue

            # we are going well
            notes['dl_files'].append(path)

            # delete file in logger
            rv = await lc.cmd_del(del_name)
            _rae(rv, "del")
            lg.a("deleted file {}".format(del_name))

            # create LEF file with download info
            lg.a("creating file LEF for {}".format(name))
            dds_create_file_lef(g, name)
            _gear_type = ddh_get_cfg_gear_type()
            if _gear_type == 0:
                dds_create_file_fixed_gpq(g, name)

        # format file-system, o/w DO-1 loggers (NAND mem) get slower
        await asyncio.sleep(.1)
        rv = await lc.cmd_frm()
        _rae(rv, "frm")
        lg.a("FRM | OK")

        # restore the logger config file
        path = str(get_dl_folder_path_from_mac(mac) / MC_FILE)
        with open(path) as f:
            j = json.load(f)
            rv = await lc.cmd_cfg(j)
            _rae(rv, "cfg")
            lg.a("CFG | OK")

        # see if the DO sensor works
        for i_do in range(3):
            rv = await lc.cmd_gdo()
            bad_rv = not rv or (rv and rv[0] == "0000")
            if not bad_rv:
                # good!
                lg.a("GDO | {}".format(rv))
                break
            # GDO went south, check number of retries remaining
            lg.a(f"GDO | error {rv}")
            if i_do == 2:
                # notify this
                lat, lon, _, __ = g
                ln = LoggerNotification(mac, sn, 'DOX', b)
                ln.uuid_interaction = u
                notify_logger_error_sensor_oxygen(g, ln)
                _une(bad_rv, notes, "ox_sensor_error", ce=1)
                _rae(bad_rv, "gdo")
            else:
                _u(STATE_DDS_BLE_DOWNLOAD_ERROR_GDO)
                _une(bad_rv, notes, "ox_sensor_error", ce=0)
            await asyncio.sleep(5)

        # see if this guy has GDX (better GDO) instruction
        await asyncio.sleep(1)
        rv = await lc.cmd_gdx()
        lg.a(f"GDX | (beta) {rv}")
        await asyncio.sleep(1)

        # wake mode
        w = "on" if rerun_flag else "off"
        rv = await lc.cmd_wak(w)
        _rae(rv, "wak")
        lg.a(f"WAK | {w} OK")

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
            _u(f"{STATE_DDS_BLE_RUN_STATUS}/off")
            notes['rerun'] = False
            # give time to GUI to display
            await asyncio.sleep(5)

        # -----------------------
        # bye, bye to this logger
        # -----------------------
        await lc.disconnect()
        return 0


async def ble_interact_do1_or_do2(mac, info, g, h, u):

    rv = 0
    notes = {}
    lc = BleCC26X2(h)

    try:
        # -------------------------
        # BLE connection done here
        # -------------------------
        lg.a(f"interacting with DO logger: {info}")
        rv = await BleCC26X2Download.download_recipe(lc,
                                                     mac,
                                                     g,
                                                     notes,
                                                     u)

    except Exception as ex:
        await lc.disconnect()
        lg.a(f"error dl_cc26x2r_exception {ex}")
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
    _m = "60:77:71:22:CA:6A"
    _i = "DO-2"
    _g = ("+1.111111", "-2.222222", datetime.datetime.now(), 0)
    _h = "hci0"
    _args = [_m, _i, _g, _h]
    ael.run_until_complete(ble_interact_do1_or_do2(*_args))
