import datetime
import pathlib
import shutil
import time
from tzlocal import get_localzone

from ddh.utils_graph import utils_graph_set_fol_req_file
from dds.ble_dl_tdo import ble_interact_tdo
from dds.macs import (
    rm_mac_black,
    add_mac_black,
    rm_mac_orange,
    is_mac_in_black,
    is_mac_in_orange,
    add_mac_orange,
)
from dds.notifications import notify_logger_download, \
    notify_logger_error_retries, LoggerNotification
from dds.timecache import its_time_to
from mat.ble.ble_mat_utils import (ble_mat_get_antenna_type,
                                   ble_mat_systemctl_restart_bluetooth)
from dds.ble_dl_rn4020 import ble_interact_rn4020
from dds.ble_dl_dox import ble_interact_do1_or_do2
from dds.gps import gps_tell_position_logger
from mat.lix import id_lid_file_flavor, LID_FILE_V2, convert_lix_file
from mat.utils import linux_is_rpi
from utils.ddh_config import (dds_get_cfg_flag_purge_this_mac_dl_files_folder,
                              dds_get_cfg_logger_sn_from_mac)
from utils.ddh_shared import (
    send_ddh_udp_gui as _u,
    STATE_DDS_BLE_DOWNLOAD_OK,
    STATE_DDS_BLE_DOWNLOAD_ERROR,
    STATE_DDS_BLE_DOWNLOAD_WARNING,
    get_dl_folder_path_from_mac,
    STATE_DDS_BLE_DOWNLOAD, dds_get_aws_has_something_to_do_via_gui_flag_file,
    STATE_DDS_NOTIFY_HISTORY, STATE_DDS_BLE_ERROR_MOANA_PLUGIN,
    STATE_DDS_BLE_CONNECTING,
    STATE_DDS_REQUEST_GRAPH,
)
from utils.logs import lg_dds as lg
from dds.ble_dl_moana import ble_interact_moana


_g_logger_errors = {}


def _ble_tell_logger_seen(mac, _b, _o):
    if its_time_to(f'tell_saw_mac_{mac}', 1800):
        sn = dds_get_cfg_logger_sn_from_mac(mac)
        lg.a(f"warning: logger {sn} / mac {mac} nearby")
        if _b:
            lg.a(f"warning: logger is under long forget time")
        if _o:
            lg.a(f"warning: logger is under short forget time")


def _ble_convert_lid(ls_lid):
    for f in ls_lid:
        # f: absolute file path ending in .lid
        if id_lid_file_flavor(f) != LID_FILE_V2:
            continue
        lg.a(f"after download converting LID file v2 {f}")
        convert_lix_file(f)
        lg.a(f"OK: after download converted LID file v2 {f}")


def _ble_analyze_logger_result(rv, g, ln: LoggerNotification, err_critical):

    # grab variables
    mac = ln.mac
    sn = ln.sn

    # success :)
    if rv == 0:
        rm_mac_black(mac)
        rm_mac_orange(mac)
        add_mac_black(mac)
        notify_logger_download(g, ln)
        if mac in _g_logger_errors.keys():
            del _g_logger_errors[mac]
        lg.a(f"OK! logger {mac}/{sn}")
        _u(f"{STATE_DDS_BLE_DOWNLOAD_OK}/{sn}")
        time.sleep(1)

        # graph loggers just downloaded
        utils_graph_set_fol_req_file(mac)
        lg.a(f"requesting auto-graph for {mac}")
        _u(STATE_DDS_REQUEST_GRAPH)
        return

    # NOT success
    if mac not in _g_logger_errors:
        # CREATE error entry for this mac
        _g_logger_errors[mac] = 1
        rm_mac_black(mac)
    else:
        # INCREASE error entry for this mac
        _g_logger_errors[mac] += 1

    # speed up things
    if err_critical:
        _g_logger_errors[mac] = 5

    if _g_logger_errors[mac] >= 5:
        rm_mac_orange(mac)
        add_mac_black(mac)
        lg.a(f"error: logger {mac}/{sn} totally failed, critical = {err_critical}")
        _u(f"{STATE_DDS_BLE_DOWNLOAD_ERROR}/{sn}")
        notify_logger_error_retries(g, ln)
        _g_logger_errors[mac] = 0

    else:
        rm_mac_orange(mac)
        add_mac_orange(mac)
        lg.a(f"warning: logger {mac}/{sn} NOT done")
        _u(f"{STATE_DDS_BLE_DOWNLOAD_WARNING}/{sn}")


def _ble_logger_is_do1_or_do2(info: str):
    return "DO-" in info


def _ble_logger_is_tdo(info: str):
    return "TDO" in info


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
    # mac = '60:77:71:22:c8:6f'
    # info = 'DO-2'

    # debug: delete THIS logger's existing files
    if dds_get_cfg_flag_purge_this_mac_dl_files_folder():
        lg.a("debug: HOOK_PURGE_THIS_MAC_DL_FILES_FOLDER {}".format(mac))
        p = pathlib.Path(get_dl_folder_path_from_mac(mac))
        shutil.rmtree(str(p), ignore_errors=True)

    # get logger serial number
    sn = dds_get_cfg_logger_sn_from_mac(mac)
    _u(f"{STATE_DDS_BLE_DOWNLOAD}/{sn}")
    lg.a(f"processing sensor {sn} / mac {mac}")

    # bleak wants a string, not an integer
    hs = "hci{}".format(h)

    # separate g
    lat, lon, dt, _ = g

    # in case 'g' is NOT-WHOLE here
    if lat == "":
        lg.a("error: lat is empty for logger {}".format(sn))
        _u("history/add&{}&error&{}&{}&{}".format(mac, lat, lon, dt))
        # 0 because this is not a BLE interaction error
        return 0

    # allows discarding loggers faster
    _crit_error = False
    _error_dl = ""

    # some GUI update
    _u(f"{STATE_DDS_BLE_CONNECTING}/{sn}")

    # --------------------
    # logger interaction
    # --------------------
    if _ble_logger_is_do1_or_do2(info):
        rv, notes = await ble_interact_do1_or_do2(mac, info, g, hs)
        _crit_error = notes["crit_error"]
        _error_dl = notes["error"]
        _ble_convert_lid(notes["dl_files"])

    elif _ble_logger_is_rn4020(mac, info):
        rv = await ble_interact_rn4020(mac, info, g, hs)

    elif _ble_logger_is_moana(info):
        fol = get_dl_folder_path_from_mac(mac)
        rv = await ble_interact_moana(fol, mac, hs, g)
        if rv == 2:
            _u(STATE_DDS_BLE_ERROR_MOANA_PLUGIN)
            if its_time_to(f'tell_error_moana_plugin', 900):
                lg.a('error: no Moana plugin installed')
            time.sleep(5)
            # 0 because this is not a BLE interaction error
            return 0

    elif _ble_logger_is_tdo(info):
        rv, notes = await ble_interact_tdo(mac, info, g, hs)
        _crit_error = notes["crit_error"]
        _error_dl = notes["error"]
        _ble_convert_lid(notes["dl_files"])

    else:
        lg.a(f'error: this should not happen, info {info}')
        # 0 because this is not a BLE interaction error
        return 0

    # tell GUI how it went, also do MAC colors stuff
    try:
        bat = notes["battery_level"]
    except (Exception, ):
        # moana does not have this
        bat = 0
    ln = LoggerNotification(mac, sn, info, bat)
    _ble_analyze_logger_result(rv, g, ln, _crit_error)

    # -----------------------------------------------------------------
    # on OK and error, w/o this some external antennas don't scan again
    # -----------------------------------------------------------------
    _, ta = ble_mat_get_antenna_type()
    if ta == 'external' and linux_is_rpi():
        lg.a('warning: external antenna requires reset tweak')
        ble_mat_systemctl_restart_bluetooth()

    # on GUI, all times are local, not UTC
    tz_ddh = get_localzone()
    tz_utc = datetime.timezone.utc
    dt_local = dt.replace(tzinfo=tz_utc).astimezone(tz=tz_ddh)

    # ------------------------------------
    # so GUI can update its HISTORY tab
    # ------------------------------------
    ep_loc = int(dt_local.timestamp())
    ep_utc = int(dt.timestamp())
    e = 'ok' if not rv else _error_dl
    _u(f"{STATE_DDS_NOTIFY_HISTORY}/add&"
       f"{mac}&{e}&{lat}&{lon}&{ep_loc}&{ep_utc}")

    # AWS flag only set on rpi, it is checked later after all loggers end
    try:
        if linux_is_rpi() and not rv:
            flag = dds_get_aws_has_something_to_do_via_gui_flag_file()
            pathlib.Path(flag).touch()
            lg.a("created AWS flag file")
    except (Exception, ):
        lg.a('error: creating AWS flag file')
    return rv


async def ble_interact_all_loggers(macs_det, macs_mon, g, _h: int, _h_desc):

    for mac, model in macs_det.items():
        # because macs_det, macs_mon macs_mon are lowercase
        mac = mac.lower()
        if mac not in macs_mon:
            continue

        _b = is_mac_in_black(mac)
        _o = is_mac_in_orange(mac)

        # helps in distance-detection issues
        _ble_tell_logger_seen(mac, _b, _o)

        if _b or _o:
            continue

        # show the position of the logger we will download
        gps_tell_position_logger(g)

        # MAC passed all filters, work with it
        return await _ble_id_n_interact_logger(mac, model, _h, g)
