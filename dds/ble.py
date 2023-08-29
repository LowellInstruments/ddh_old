import os
import pathlib
import shutil

from ddh.utils_graph import graph_set_fol_req_file
from dds.macs import (
    rm_mac_black,
    add_mac_black,
    rm_mac_orange,
    is_mac_in_black,
    is_mac_in_orange,
    add_mac_orange,
)
from mat.ble.ble_mat_utils import ble_mat_bluetoothctl_power_cycle, ble_mat_disconnect_all_devices_ll
from mat.ble.bleak.cc26x2r_sim import ble_logger_is_cc26x2r_simulated

from dds.ble_dl_rn4020 import ble_interact_rn4020
from dds.ble_dl_cc26x2r import ble_interact_cc26x2
from dds.ble_dl_moana import ble_interact_moana, check_moana_plugin_is_missing
from dds.gps import gps_tell_position_logger
from dds.sqs import (
    sqs_msg_logger_error_max_retries,
    sqs_msg_logger_download,
    sqs_msg_notes_cc26x2r,
)
from mat.utils import linux_is_rpi
from utils.ddh_shared import (
    send_ddh_udp_gui as _u,
    STATE_DDS_BLE_DOWNLOAD_OK,
    STATE_DDS_BLE_DOWNLOAD_ERROR,
    STATE_DDS_BLE_DOWNLOAD_WARNING,
    get_dl_folder_path_from_mac,
    dds_get_json_mac_dns,
    STATE_DDS_BLE_DOWNLOAD,
)
from settings.ctx import hook_ble_purge_this_mac_dl_files_folder
from utils.logs import lg_dds as lg


_g_logger_errors = {}


def _ble_analyze_logger_result(rv, mac, lat, lon, sn):
    if rv == 0:
        rm_mac_black(mac)
        rm_mac_orange(mac)
        add_mac_black(mac)
        sqs_msg_logger_download(mac, sn, lat, lon)
        if mac in _g_logger_errors.keys():
            del _g_logger_errors[mac]
        lg.a("OK! logger {}/{}".format(mac, sn))
        _u("{}/{}".format(STATE_DDS_BLE_DOWNLOAD_OK, sn))

        # new graphing engine
        # graph_set_fol_req_file(mac)
        return

    if mac not in _g_logger_errors:
        # CREATE error entry for this mac
        _g_logger_errors[mac] = 1
        rm_mac_black(mac)
    else:
        # INCREASE error entry for this mac
        _g_logger_errors[mac] += 1

    if _g_logger_errors[mac] >= 10:
        rm_mac_orange(mac)
        add_mac_black(mac)
        lg.a("error: logger {}/{} totally failed".format(mac, sn))
        _u("{}/{}".format(STATE_DDS_BLE_DOWNLOAD_ERROR, mac))
        sqs_msg_logger_error_max_retries(mac, sn, lat, lon)
        _g_logger_errors[mac] = 0

    else:
        rm_mac_orange(mac)
        add_mac_orange(mac)
        lg.a("warning: logger {}/{} NOT done".format(mac, sn))
        _u("{}/{}".format(STATE_DDS_BLE_DOWNLOAD_WARNING, sn))


def _ble_logger_is_cc26x2r(info: str):
    return "DO-" in info


def _ble_logger_is_moana(info: str):
    return "MOANA" in info


def _ble_logger_is_rn4020(mac, info):
    a = "00:1E:C0"
    if mac.startswith(a) or mac.startswith(a.lower()):
        return True
    if "MATP-2W" in info:
        return True


async def _ble_id_n_interact_logger(mac, info: str, h, g):

    # debug
    # l_d_('forcing query of hardcoded mac')
    # hc_mac = '60:77:71:22:c8:6f'
    # hc_info = 'DO-2'
    # mac = hc_mac
    # info = hc_info

    # debug: delete THIS logger's existing files
    if hook_ble_purge_this_mac_dl_files_folder:
        lg.a("debug: HOOK_PURGE_THIS_MAC_DL_FILES_FOLDER {}".format(mac))
        p = pathlib.Path(get_dl_folder_path_from_mac(mac))
        shutil.rmtree(str(p), ignore_errors=True)

    # variables
    sn = dds_get_json_mac_dns(mac)
    _u("{}/{}".format(STATE_DDS_BLE_DOWNLOAD, sn))
    lg.a("processing sensor {} / mac {}".format(sn, mac))

    # bleak wants a string, not an integer
    hs = "hci{}".format(h)

    # separate g
    lat, lon, dt, _ = g

    # g can be not whole here
    if lat == "":
        lg.a("error: lat is empty for logger {}".format(sn))
        _u("history/add&{}&error&{}&{}&{}".format(sn, lat, lon, dt))
        return

    # -------------------------
    # main logger interaction
    # -------------------------
    if _ble_logger_is_cc26x2r(info):
        rv, notes = await ble_interact_cc26x2(mac, info, g, hs)
        sqs_msg_notes_cc26x2r(notes, mac, sn, lat, lon)

    elif _ble_logger_is_rn4020(mac, info):
        rv = await ble_interact_rn4020(mac, info, g, hs)

    elif _ble_logger_is_moana(info):
        fol = get_dl_folder_path_from_mac(mac)
        rv = await ble_interact_moana(fol, mac, hs, g)
        if check_moana_plugin_is_missing(rv):
            # stop it here
            return

    # see how it went
    _ble_analyze_logger_result(rv, mac, lat, lon, sn)

    # do history things here
    if rv == 0:
        _u("history/add&{}&ok&{}&{}&{}".format(sn, lat, lon, dt))
    else:
        _u("history/add&{}&error&{}&{}&{}".format(sn, lat, lon, dt))
        # works for RPi
        ble_mat_bluetoothctl_power_cycle()
        # works for laptop
        if not linux_is_rpi():
            ble_mat_disconnect_all_devices_ll()


async def ble_interact_all_loggers(macs_det, macs_mon, g, _h: int, _h_desc):

    for mac, model in macs_det.items():

        simulated_mac = ble_logger_is_cc26x2r_simulated(mac)
        if mac not in macs_mon and not simulated_mac:
            continue
        if is_mac_in_black(mac):
            continue
        if is_mac_in_orange(mac):
            continue

        # show the position of the logger we will download
        gps_tell_position_logger(g)

        # MAC passed all filters, work with it
        await _ble_id_n_interact_logger(mac, model, _h, g)
