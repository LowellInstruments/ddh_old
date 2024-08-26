import datetime
import os
import pathlib
import shutil
import time
import uuid
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
    notify_logger_error_retries, LoggerNotification, notify_logger_dox_hypoxia
from dds.timecache import is_it_time_to
from mat.ble.ble_mat_utils import (ble_mat_systemctl_restart_bluetooth,
                                   ble_mat_get_antenna_type_v2)
from dds.ble_dl_rn4020 import ble_interact_rn4020
from dds.ble_dl_dox import ble_interact_do1_or_do2
from dds.gps import gps_tell_position_logger
from mat.data_converter import default_parameters, DataConverter
from mat.lix import id_lid_file_flavor, LID_FILE_V2, LID_FILE_V1
from mat.lix_dox import is_a_do2_file
from mat.lix_pr import convert_lix_file
from mat.utils import linux_is_rpi
from utils.ddh_config import (dds_get_cfg_flag_purge_this_mac_dl_files_folder,
                              dds_get_cfg_logger_sn_from_mac, dds_get_cfg_logger_mac_from_sn)
from utils.ddh_shared import (
    send_ddh_udp_gui as _u,
    STATE_DDS_BLE_DOWNLOAD_OK,
    STATE_DDS_BLE_DOWNLOAD_ERROR,
    STATE_DDS_BLE_DOWNLOAD_WARNING,
    get_dl_folder_path_from_mac,
    STATE_DDS_BLE_DOWNLOAD,
    STATE_DDS_NOTIFY_HISTORY, STATE_DDS_BLE_ERROR_MOANA_PLUGIN,
    STATE_DDS_BLE_CONNECTING,
    STATE_DDS_REQUEST_GRAPH,
)
from utils.logs import lg_dds as lg
from dds.ble_dl_moana import ble_interact_moana


_g_logger_errors = {}


def _ble_tell_logger_seen(mac, _b, _o):
    if is_it_time_to(f'tell_saw_mac_{mac}', 1800):
        sn = dds_get_cfg_logger_sn_from_mac(mac)
        lg.a(f"warning: logger {sn} / mac {mac} nearby")
        if _b:
            lg.a(f"warning: logger is under long forget time")
        if _o:
            lg.a(f"warning: logger is under short forget time")


def _ble_detect_hypoxia_after_download(f_lid, bat, g, u=''):
    try:
        if not f_lid.endswith('.lid') or not is_a_do2_file(f_lid):
            return
        f_csv = f_lid.replace('.lid', '_DissolvedOxygen.csv')
        if not os.path.exists(f_csv):
            return

        # f_csv: 2404725_lab_20240407_230609.csv
        sn = os.path.basename(f_csv).split('_')[0]
        mac = dds_get_cfg_logger_mac_from_sn(sn)
        ln = LoggerNotification(mac, sn, 'DOX', bat)
        ln.uuid_interaction = u
        with open(f_csv, 'r') as f:
            ll = f.readlines()
            # headers: 'ISO 8601 Time,elapsed time (s),agg. time(s),Dissolved Oxygen (mg/l)...
            for i in ll[1:]:
                do_mg_l = float(i.split(',')[3])
                if do_mg_l <= 0.0:
                    notify_logger_dox_hypoxia(g, ln)
                    break
    except (Exception, ) as ex:
        lg.a(f'error: testing _ble_detect_hypoxia -> {ex}')


def _ble_convert_lid_after_download(d):
    ls_lid = d['dl_files']
    ls_lid = [f for f in ls_lid if '.lid' in f]
    bat = d['battery_level']
    g = d['gps']
    u = d['uuid_interaction']

    for f in ls_lid:
        # f: absolute file path ending in .lid
        n = id_lid_file_flavor(f)
        lg.a(f"after download converting LID v{n} file {f}")
        if n == LID_FILE_V2:
            # ----------------------------
            # convert DOX and TDO v2 files
            # ----------------------------
            convert_lix_file(f)
            _ble_detect_hypoxia_after_download(f, bat, g, u)
        if n == LID_FILE_V1:
            # do the old MAT library conversion
            parameters = default_parameters()
            DataConverter(f, parameters).convert()
        lg.a(f"OK: after download converted LID v{n} file {f}")


def _ble_analyze_logger_result(rv,
                               g,
                               ln: LoggerNotification,
                               err_critical):

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

    # useful for dashboards and databases
    uuid_interaction = str(uuid.uuid4())

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
    hs = f"hci{h}"

    # separate g
    lat, lon, dt, _ = g

    # in case 'g' is NOT-WHOLE here
    if lat == "":
        lg.a(f"error: lat is empty for logger {sn}")
        _u(f"history/add&{mac}&error&{lat}&{lon}&{dt}")
        # 0 because this is not a BLE interaction error
        return 0

    # allows discarding loggers faster
    _crit_error = False
    _error_dl = ""

    # initialize download status
    bat = 0
    rerun = True
    do_we_have_notes = False

    # some GUI update
    _u(f"{STATE_DDS_BLE_CONNECTING}/{sn}")

    # ------------------------
    # DOX logger interaction
    # ------------------------
    if _ble_logger_is_do1_or_do2(info):
        rv, notes = await ble_interact_do1_or_do2(mac,
                                                  info,
                                                  g,
                                                  hs,
                                                  uuid_interaction)
        notes['gps'] = g
        _crit_error = notes["crit_error"]
        _error_dl = notes["error"]
        rerun = notes['rerun']
        notes['uuid_interaction'] = uuid_interaction
        do_we_have_notes = True
        _ble_convert_lid_after_download(notes)

    elif _ble_logger_is_rn4020(mac, info):
        rv = await ble_interact_rn4020(mac, info, g, hs)

    elif _ble_logger_is_moana(info):
        fol = get_dl_folder_path_from_mac(mac)
        rv = await ble_interact_moana(fol, mac, hs, g)
        if rv == 2:
            _u(STATE_DDS_BLE_ERROR_MOANA_PLUGIN)
            if is_it_time_to(f'tell_error_moana_plugin', 900):
                lg.a('error: no Moana plugin installed')
            time.sleep(5)
            # 0 because this is not a BLE interaction error
            return 0

    # -----------------------
    # TDO logger interaction
    # -----------------------
    elif _ble_logger_is_tdo(info):
        rv, notes = await ble_interact_tdo(mac,
                                           info,
                                           g,
                                           hs,
                                           uuid_interaction)
        notes['gps'] = g
        _crit_error = notes["crit_error"]
        _error_dl = notes["error"]
        rerun = notes['rerun']
        notes['uuid_interaction'] = uuid_interaction
        do_we_have_notes = True
        _ble_convert_lid_after_download(notes)

    else:
        lg.a(f'error: this should not happen, info {info}')
        # 0 because this is not a BLE interaction error
        return 0

    # -----------------------------------------------------------------
    # on OK and error, w/o this some external antennas don't scan again
    # -----------------------------------------------------------------
    _, ta = ble_mat_get_antenna_type_v2()
    if ta == 'external' and linux_is_rpi():
        lg.a('warning: external antenna requires reset tweak')
        ble_mat_systemctl_restart_bluetooth()

    # on GUI, all times are local, not UTC
    tz_ddh = get_localzone()
    tz_utc = datetime.timezone.utc
    dt_local = dt.replace(tzinfo=tz_utc).astimezone(tz=tz_ddh)

    # complete logger notification with interaction UUID
    ln = LoggerNotification(mac, sn, info, bat)
    ln.uuid_interaction = uuid_interaction
    if do_we_have_notes:
        ln.dl_files = notes['dl_files']
        ln.gfv = notes['gfv']
        ln.bat = notes['battery_level']

    # ----------------------------
    # so we can plot this logger
    # ----------------------------
    _ble_analyze_logger_result(rv, g, ln, _crit_error)

    # ------------------------------------
    # so GUI can update its HISTORY tab
    # ------------------------------------
    ep_loc = int(dt_local.timestamp())
    ep_utc = int(dt.timestamp())
    # ensure value for error_dl is populated
    if not _error_dl:
        _error_dl = 'error comm.'
    e = 'ok' if not rv else _error_dl

    # print('ep_loc', ep_loc)
    # print('ep_utc', ep_utc)

    _u(f"{STATE_DDS_NOTIFY_HISTORY}/add&"
       f"{mac}&{e}&{lat}&{lon}&{ep_loc}&{ep_utc}&{rerun}&{uuid_interaction}")

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
