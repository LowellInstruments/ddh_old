import asyncio
import datetime
import os
from dds.gpq import gpq_create_fixed_mode_file
from dds.lef import lef_create_file
from dds.notifications_v2 import (notify_logger_error_sensor_pressure,
                                  notify_logger_error_low_battery,
                                  LoggerNotification)
from mat.ble.ble_mat_utils import (
    ble_mat_crc_local_vs_remote,
    DDH_GUI_UDP_PORT, ble_mat_disconnect_all_devices_ll,
)
from mat.ble.bleak.cc26x2r import BleCC26X2
from dds.ble_utils_dds import ble_logger_ccx26x2r_needs_a_reset, dds_ble_init_rv_notes
from mat.utils import linux_is_rpi
from utils.ddh_config import (ddh_get_cfg_gear_type, dds_get_cfg_logger_sn_from_mac,
                              dds_get_cfg_flag_download_test_mode)
from utils.ddh_shared import (
    send_ddh_udp_gui as _u,
    STATE_DDS_BLE_ERROR_RUN,
    STATE_DDS_BLE_DOWNLOAD_ERROR_TP_SENSOR,
    BLEAppException, ael, get_ddh_do_not_rerun_flag_li,
    TESTMODE_FILENAMEPREFIX, STATE_DDS_BLE_DOWNLOAD_PROGRESS,
    STATE_DDS_BLE_LOW_BATTERY
)
from utils.logs import lg_dds as lg
from utils.ddh_shared import (
    get_dl_folder_path_from_mac,
    create_folder_logger_by_mac,
)


g_debug_not_delete_files = False
BAT_FACTOR_TDO = 0.5454


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

    # ---------------------
    # download fast method
    # ---------------------

    @staticmethod
    async def dl_fast(lc, mac, g, notes: dict, u):

        # DDH "A" command includes GTM, SWS, DIR
        rv, ls = await lc.cmd_ddh_a(g)
        _rae(rv, "DDA error listing files: " + str(rv))
        lg.a(f"DIR: {ls}")
        _u(f"{STATE_DDS_BLE_DOWNLOAD_PROGRESS}/{0}")

        # iterate files present in logger
        for name, size in ls.items():
            # delete zero-bytes files
            if size == 0:
                rv = await lc.cmd_del(name)
                _rae(rv, "del")
                continue

            # download file
            lg.a(f"downloading file {name}")
            rv = await lc.cmd_dwg(name)
            _rae(rv, "dwg")
            up = DDH_GUI_UDP_PORT
            rv, d = await lc.cmd_dwl(int(size), ip="127.0.0.1", port=up)
            _rae(rv, "dwl")
            file_data = lc.ans

            # keep original filename from logger
            del_name = name

            # save file in our local disk
            if dds_get_cfg_flag_download_test_mode():
                name = TESTMODE_FILENAMEPREFIX + name
            path = str(get_dl_folder_path_from_mac(mac) / name)
            with open(path, "wb") as f:
                f.write(file_data)
            lg.a(f"downloaded file {name}")

            # add to the output list
            notes['dl_files'].append(path)

            # delete file in logger
            global g_debug_not_delete_files
            if g_debug_not_delete_files:
                lg.a('warning: test, we are NOT deleting files')
            else:
                rv = await lc.cmd_del(del_name)
                _rae(rv, "del")
                lg.a(f"deleted file {del_name}")

            # create LEF file with download info
            lg.a(f"creating file LEF for {name}")
            lef_create_file(g, name)

            # create CST file
            _gear_type = ddh_get_cfg_gear_type()
            if _gear_type == 0:
                gpq_create_fixed_mode_file(g, name)

        # DDH "B" command includes STM, BAT, FRM, RWS
        do_we_rerun = not get_ddh_do_not_rerun_flag_li()
        rv, v = await lc.cmd_ddh_b(rerun=do_we_rerun)
        _rae(rv, "ddh_b")
        # a: b'__B 200020000000F072022/08/25 12:13:55'
        v = v[17:19] + v[15:17]
        b = int(v, 16)
        adc_b = b
        b /= BAT_FACTOR_TDO
        notes["battery_level"] = b
        lg.a(f"DDB: battery ADC {adc_b} mV -> {b} mV")
        if adc_b < 982:
            sn = dds_get_cfg_logger_sn_from_mac(mac)
            ln = LoggerNotification(mac, sn, 'TDO', adc_b)
            ln.uuid_interaction = u
            notify_logger_error_low_battery(g, ln)
            _u(f"{STATE_DDS_BLE_LOW_BATTERY}/{mac}")
            # give time to GUI to display
            await asyncio.sleep(3)

        notes['rerun'] = do_we_rerun
        if not do_we_rerun:
            lg.a("warning: this logger is not set for auto-re-run")

        # -----------------------
        # bye, bye to this logger
        # -----------------------
        await lc.disconnect()
        return 0

    @staticmethod
    async def download_recipe(lc, mac, g, notes: dict, u):

        dds_ble_init_rv_notes(notes)
        create_folder_logger_by_mac(mac)
        sn = dds_get_cfg_logger_sn_from_mac(mac)

        rv = await lc.connect(mac)
        _une(rv, notes, "comm.")
        _rae(rv, "connecting")
        lg.a(f"connected to {mac}")

        if ble_logger_ccx26x2r_needs_a_reset(mac):
            await lc.cmd_rst()
            # out of here for sure
            raise BLEAppException("TDO interact logger reset file")

        rv, v = await lc.cmd_gfv()
        _rae(rv, "gfv")
        lg.a(f"GFV | {v}")
        notes['gfv'] = v
        # --------------------------------------
        # for newer loggers with super commands
        # --------------------------------------
        if v >= "4.0.04":
            lg.a("---------------------------")
            lg.a("running DL TDO fast version")
            lg.a("---------------------------")
            return await BleTDODownload.dl_fast(lc, mac, g, notes, u)
        else:
            lg.a("-----------------------------")
            lg.a("running DL TDO normal version")
            lg.a("-----------------------------")

        rv, state = await lc.cmd_sts()
        _rae(rv, "sts")
        lg.a(f"STS | logger was {state}")

        rv = await lc.cmd_sws(g)
        _rae(rv, "sws")
        lg.a("SWS | OK")

        rv, t = await lc.cmd_utm()
        _rae(rv, "utm")
        lg.a(f"UTM | {t}")

        rv, b = await lc.cmd_bat()
        _rae(rv, "bat")
        adc_b = b
        b /= BAT_FACTOR_TDO
        lg.a(f"BAT | ADC {adc_b} mV -> {b} mV")
        notes["battery_level"] = b
        if adc_b < 982:
            ln = LoggerNotification(mac, sn, 'TDO', adc_b)
            ln.uuid_interaction = u
            notify_logger_error_low_battery(g, ln)
            _u(f"{STATE_DDS_BLE_LOW_BATTERY}/{mac}")
            # give time to GUI to display
            await asyncio.sleep(3)

        rv, v = await lc.cmd_gtm()
        _rae(rv, "gtm")
        lg.a(f"GTM | {v}")

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
        lg.a(f"DIR | {ls}")

        # iterate files present in logger
        for name, size in ls.items():

            # delete zero-bytes files
            if size == 0:
                rv = await lc.cmd_del(name)
                _rae(rv, "del")
                continue

            # download file
            lg.a(f"downloading file {name}")
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
                lg.a(f"error: bad CRC so removing local file {path}")
                os.unlink(path)

            # save file in our local disk
            del_name = name
            if dds_get_cfg_flag_download_test_mode():
                name = TESTMODE_FILENAMEPREFIX + name
            path = str(get_dl_folder_path_from_mac(mac) / name)
            with open(path, "wb") as f:
                f.write(file_data)
            lg.a(f"downloaded file {name}")

            # add to the output list
            notes['dl_files'].append(path)

            # delete file in logger
            rv = await lc.cmd_del(del_name)
            _rae(rv, "del")
            lg.a(f"deleted file {del_name}")

            # create LEF file with download info
            lg.a(f"creating file LEF for {name}")
            lef_create_file(g, name)

            # create CST file when fixed mode
            _gear_type = ddh_get_cfg_gear_type()
            if _gear_type == 0:
                gpq_create_fixed_mode_file(g, name)

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
            lg.a(f'GST | error {rv}')
            _u(STATE_DDS_BLE_DOWNLOAD_ERROR_TP_SENSOR)
            await asyncio.sleep(5)
        _rae(bad_rv, "gst")

        # check sensors measurement, Pressure
        rv = await lc.cmd_gsp()
        # rv: (0, 1241)
        bad_rv = not rv or rv[0] == 1 or rv[1] == 0xFFFF or rv[1] == 0
        if bad_rv:
            _une(bad_rv, notes, "P_sensor_error", ce=1)
            lg.a(f'GSP | error {rv}')
            ln = LoggerNotification(mac, sn, 'TDO', b)
            ln.uuid_interaction = u
            notify_logger_error_sensor_pressure(g, ln)
            _u(STATE_DDS_BLE_DOWNLOAD_ERROR_TP_SENSOR)
            await asyncio.sleep(5)
        _rae(bad_rv, "gsp")

        # get the rerun flag
        rerun_flag = not get_ddh_do_not_rerun_flag_li()

        # wake mode
        w = "on" if rerun_flag else "off"
        rv = await lc.cmd_wak(w)
        _rae(rv, "wak")
        lg.a(f"WAK | {w} OK")
        await asyncio.sleep(1)

        notes['rerun'] = rerun_flag
        if rerun_flag:
            rv = await lc.cmd_rws(g)
            if rv:
                _u(STATE_DDS_BLE_ERROR_RUN)
                await asyncio.sleep(5)
            _rae(rv, "rws")
            lg.a("RWS | OK")
        else:
            lg.a("warning: telling this logger is not set for auto-re-run")

        # -----------------------
        # bye, bye to this logger
        # -----------------------
        await lc.disconnect()
        return 0


async def ble_interact_tdo(mac, info, g, h, u):

    rv = 0
    notes = {}
    lc = BleCC26X2(h)

    try:
        lg.a(f"interacting {info} logger")
        rv = await BleTDODownload.download_recipe(lc, mac, g, notes, u)

    except Exception as ex:
        await lc.disconnect()
        lg.a(f"error dl_tdo_exception {ex}")
        rv = 1

    finally:
        return rv, notes


# ------
# test
# ------
if __name__ == "__main__":
    ble_mat_disconnect_all_devices_ll()
    # we currently in 'ddh/dds'
    os.chdir('')
    _m = "D0:2E:AB:D9:29:48"
    _i = "TDO"
    _g = ("+1.111111", "-2.222222", datetime.datetime.now(), 0)
    _h = "hci0"
    _args = [_m, _i, _g, _h]
    ael.run_until_complete(ble_interact_tdo(*_args))
