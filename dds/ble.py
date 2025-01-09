import datetime
import os
import pathlib
import shutil
import subprocess as sp
import uuid

import time
from tzlocal import get_localzone

from ddh.utils_graph import utils_graph_set_fol_req_file
from dds.aws import aws_cp
from dds.ble_dl_dox import ble_interact_do1_or_do2
from dds.ble_dl_dox_lsb import ble_interact_dox_lsb
from dds.ble_dl_moana import ble_interact_moana
from dds.ble_dl_rn4020 import ble_interact_rn4020
from dds.ble_dl_tdo import ble_interact_tdo
from dds.ble_dl_tdo_lsb import ble_interact_tdo_lsb
from dds.gps import gps_log_position_logger, gps_simulate_boat_speed
from dds.in_ports_geo import dds_ask_in_port_to_ddn
from dds.macs import (
    rm_mac_black,
    add_mac_black,
    rm_mac_orange,
    is_mac_in_black,
    is_mac_in_orange,
    add_mac_orange,
)
from dds.notifications_v2 import (
    notify_logger_download,
    notify_logger_error_retries,
    LoggerNotification,
    notify_logger_dox_hypoxia,
    notify_ddh_error_hw_ble
)
from dds.state import ddh_state
from dds.timecache import is_it_time_to
from mat.ble.ble_mat_utils import (
    ble_mat_systemctl_restart_bluetooth,
    ble_mat_get_antenna_type_v2
)
from mat.data_converter import default_parameters, DataConverter
from mat.lix import id_lid_file_flavor, LID_FILE_V2, LID_FILE_V1
from mat.lix_dox import is_a_do2_file
from mat.lix_pr import convert_lix_file
from mat.utils import linux_is_rpi
from utils.ddh_config import (
    dds_get_cfg_flag_purge_this_mac_dl_files_folder,
    dds_get_cfg_logger_sn_from_mac,
    dds_get_cfg_logger_mac_from_sn,
    exp_get_use_lsb_for_tdo_loggers,
    exp_get_use_lsb_for_dox_loggers,
    exp_get_use_aws_cp,
    dds_get_cfg_monitored_macs,
    ddh_get_cfg_gear_type,
    dds_get_cfg_moving_speed
)
from utils.ddh_shared import (
    send_ddh_udp_gui as _u,
    STATE_DDS_BLE_DOWNLOAD_OK,
    STATE_DDS_BLE_DOWNLOAD_ERROR,
    STATE_DDS_BLE_DOWNLOAD_WARNING,
    get_dl_folder_path_from_mac,
    STATE_DDS_BLE_DOWNLOAD,
    STATE_DDS_NOTIFY_HISTORY,
    STATE_DDS_BLE_ERROR_MOANA_PLUGIN,
    STATE_DDS_BLE_CONNECTING,
    STATE_DDS_REQUEST_GRAPH,
    get_ddh_do_not_rerun_flag_li,
    STATE_DDS_BLE_RUN_STATUS,
    STATE_DDS_BLE_HARDWARE_ERROR,
    ddh_get_disabled_ble_flag_file,
    STATE_DDS_BLE_DISABLED,
    ddh_get_app_override_flag_file,
    STATE_DDS_GPS_IN_PORT,
    STATE_DDS_BLE_SCAN,
    STATE_DDS_BLE_NO_ASSIGNED_LOGGERS,
    STATE_DDS_BLE_APP_GPS_ERROR_SPEED,
    STATE_DDS_BLE_ANTENNA,
)
from utils.logs import lg_dds as lg


_g_logger_errors = {}


def _ble_show_logger_spotted(mac, _b, _o):
    if is_it_time_to(f'tell_saw_mac_{mac}', 1800):
        sn = dds_get_cfg_logger_sn_from_mac(mac)
        lg.a(f"logger {sn} / mac {mac} nearby")
        if _b:
            lg.a(f"logger {sn} is under long forget time")
        if _o:
            lg.a(f"logger {sn} under short forget time")


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
        _bn = os.path.basename(f)
        n = id_lid_file_flavor(f)
        lg.a(f"post-download conversion of LID v{n} file {_bn} started")

        # ----------------------------
        # convert DOX and TDO v2 files
        # ----------------------------
        if n == LID_FILE_V2:
            convert_lix_file(f)
            _ble_detect_hypoxia_after_download(f, bat, g, u)

        if n == LID_FILE_V1:
            # do the old MAT library conversion
            parameters = default_parameters()
            DataConverter(f, parameters).convert()
        lg.a(f"OK: post-download conversion of LID v{n} file {_bn} ended")


def _ble_analyze_and_graph_logger_result(rv,
                                         g,
                                         ln: LoggerNotification,
                                         err_critical):

    # grab variables
    mac = ln.mac
    sn = ln.sn

    # success, update GUI with rerun
    if rv == 0:
        rm_mac_black(mac)
        rm_mac_orange(mac)
        add_mac_black(mac)
        notify_logger_download(g, ln)
        if mac in _g_logger_errors.keys():
            del _g_logger_errors[mac]
        lg.a(f"OK! all done for logger {mac}/{sn}")
        if get_ddh_do_not_rerun_flag_li():
            _u(f"{STATE_DDS_BLE_RUN_STATUS}/off")
        else:
            _u(f"{STATE_DDS_BLE_DOWNLOAD_OK}/{sn}")

        # ------------------------------
        # graph loggers just downloaded
        # ------------------------------
        utils_graph_set_fol_req_file(mac)
        lg.a(f"triggering post-download graph for logger {sn}, mac {mac}")
        _u(STATE_DDS_REQUEST_GRAPH)
        return

    # NOT success
    if mac not in _g_logger_errors:
        _g_logger_errors[mac] = 1
        rm_mac_black(mac)
    else:
        _g_logger_errors[mac] += 1

    # NOT success, and the thing is serious
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


async def _ble_interact_one_logger(mac, info: str, h, g):

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
    lg.a(f"processing logger {sn} / mac {mac}")

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

    # initialize download status
    _crit_error = False
    _error_dl = ""
    bat = 0
    rerun = True
    _we_took_dl_notes = False

    # update GUI with connection icon
    _u(f"{STATE_DDS_BLE_CONNECTING}/{sn}")

    # ------------------------
    # DOX logger interaction
    # ------------------------
    if _ble_logger_is_do1_or_do2(info):
        if exp_get_use_lsb_for_dox_loggers() == 1:
            rv, notes = ble_interact_dox_lsb(mac, info, g, hs, uuid_interaction)
        else:
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
        _we_took_dl_notes = True
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
        if exp_get_use_lsb_for_tdo_loggers() == 1:
            rv, notes = ble_interact_tdo_lsb(mac, info, g, hs, uuid_interaction)
        else:
            rv, notes = await ble_interact_tdo(mac, info, g,
                                               hs, uuid_interaction)
        notes['gps'] = g
        _crit_error = notes["crit_error"]
        _error_dl = notes["error"]
        rerun = notes['rerun']
        notes['uuid_interaction'] = uuid_interaction
        _we_took_dl_notes = True
        _ble_convert_lid_after_download(notes)

    else:
        lg.a(f'error: this should not happen, info {info}')
        # 0 because not a BLE interaction error
        return 0

    # -----------------------------------------------------------------
    # on OK and error, w/o this some external antennas don't scan again
    # -----------------------------------------------------------------
    _, antenna_type_str = ble_mat_get_antenna_type_v2()
    if antenna_type_str == 'external' and linux_is_rpi():
        # some BLE dongles need a reset after download
        lg.a('debug: planned reset of BLE dongle')
        ddh_state.state_set_ble_reset_req()

    # on GUI, all times are local, we don't use UTC on GUI
    tz_ddh = get_localzone()
    tz_utc = datetime.timezone.utc
    dt_local = dt.replace(tzinfo=tz_utc).astimezone(tz=tz_ddh)

    # complete logger notification with interaction UUID
    ln = LoggerNotification(mac, sn, info, bat)
    ln.uuid_interaction = uuid_interaction
    if _we_took_dl_notes:
        ln.dl_files = notes['dl_files']
        ln.gfv = notes['gfv']
        ln.bat = notes['battery_level']
        if exp_get_use_aws_cp() == 1:
            aws_cp(notes['dl_files'])

    # plot this logger download
    _ble_analyze_and_graph_logger_result(rv, g, ln, _crit_error)

    # -------------------------------
    # GUI update HISTORY tab's table
    # -------------------------------
    ep_loc = int(dt_local.timestamp())
    ep_utc = int(dt.timestamp())
    # ensure value for error_dl is populated
    if not _error_dl:
        _error_dl = 'error comm.'
    e = 'ok' if not rv else _error_dl
    # print('ep_loc', ep_loc)
    # print('ep_utc', ep_utc)
    _u(f"{STATE_DDS_NOTIFY_HISTORY}/add&"
       f"{mac}&{e}&{lat}&{lon}&{ep_loc}&{ep_utc}&{rerun}&{uuid_interaction}&{info}")

    return rv


async def ble_interact_all_loggers(macs_det, macs_mon, g, _h: int, _h_desc):

    for mac, model in macs_det.items():
        mac = mac.lower()
        if mac not in macs_mon:
            continue

        _b = is_mac_in_black(mac)
        _o = is_mac_in_orange(mac)

        # small helps in distance-detection issues
        _ble_show_logger_spotted(mac, _b, _o)

        if _b or _o:
            continue

        # show the position of the logger we will download
        gps_log_position_logger(g)

        # work with ONE logger of the scanned ones
        return await _ble_interact_one_logger(mac, model, _h, g)


def ble_show_monitored_macs():
    mm = dds_get_cfg_monitored_macs()
    if mm:
        lg.a('monitored macs list: ')
    for i in mm:
        lg.a(f"    - {i}")


def ble_op_conditions_met(g) -> bool:

    lat, lon, tg, knots = g

    # when Bluetooth is disabled
    if os.path.isfile(ddh_get_disabled_ble_flag_file()):
        _u(STATE_DDS_BLE_DISABLED)
        return False

    # we are forced to BLE work, ex: button 2 is pressed
    flag = ddh_get_app_override_flag_file()

    # are we in port
    are_we_in_port = dds_ask_in_port_to_ddn(g)
    if are_we_in_port and not os.path.isfile(flag):
        _u(STATE_DDS_GPS_IN_PORT)
        return False

    # seems we are allowed to start working, let's scan
    _u(STATE_DDS_BLE_SCAN)

    # when it is forced to work
    if os.path.isfile(flag):
        lg.a("debug: application override set")
        os.unlink(flag)
        return True

    # case: forgot to assign loggers
    if not dds_get_cfg_monitored_macs():
        _u(STATE_DDS_BLE_NO_ASSIGNED_LOGGERS)
        time.sleep(5)
        return False

    # boat speed matters depending on haul type
    l_h = ddh_get_cfg_gear_type()
    if not l_h:
        # fixed gear case
        return True

    # CASE: trawling, we know for sure l_h is set here
    speed_range = dds_get_cfg_moving_speed()
    s_lo, s_hi = speed_range
    s_lo = float(s_lo)
    knots = float(knots)
    s_hi = float(s_hi)

    # simulation of boat speed
    s_lo, knots, s_hi = gps_simulate_boat_speed(s_lo, knots, s_hi)

    # check we are on valid boat moving range
    if s_lo <= knots <= s_hi:
        return True

    _u(f"{STATE_DDS_BLE_APP_GPS_ERROR_SPEED}/{knots}")
    time.sleep(2)


def ble_show_antenna_type(_h, desc):
    _ad = f"hci{_h}"
    s = f"debug: using {desc} bluetooth antenna, adapter {_ad}"
    if is_it_time_to(s, 60):
        # update GUI field
        _u(f"{STATE_DDS_BLE_ANTENNA}/{desc} radio")

    # run this once a day at most
    if is_it_time_to('tell_gui_antenna_type', 86400):
        lg.a(s)


def ble_check_antenna_up_n_running(g, h: int):

    # maybe we were asked to reset the interfaces
    if ddh_state.state_get_ble_reset_req():
        ddh_state.state_clr_ble_reset_req()
        for i in range(2):
            if linux_is_rpi():
                lg.a(f"warning: hciconfig reset on hci{i} upon set_ble_reset_req")
                cr = f"sudo hciconfig hci{i} reset"
                sp.run(cr, shell=True, stdout=sp.PIPE, stderr=sp.PIPE)
            else:
                lg.a(f"non-rpi CANNOT hciconfig reset on hci{i}")
        time.sleep(2)

    # read the interfaces state
    cr = f"hciconfig hci{h} | grep 'UP RUNNING'"
    rv = sp.run(cr, shell=True, stdout=sp.PIPE, stderr=sp.PIPE)
    if rv.returncode == 0:
        return True

    # know the error so re-run this
    cr = f"hciconfig hci{h}"
    rv = sp.run(cr, shell=True, stdout=sp.PIPE, stderr=sp.PIPE)
    lg.a(f'debug: out stream BLE {rv.stdout}')
    lg.a(f'debug: err stream BLE {rv.stderr}')

    # not UP and running, tell to GUI
    e = f"error: ble_check_antenna_up_n_running #{h}"
    _u(STATE_DDS_BLE_HARDWARE_ERROR)
    time.sleep(5)

    # not UP and running, tell via e-mail
    if is_it_time_to(e, 600):
        lg.a(e.format(e))
        notify_ddh_error_hw_ble(g)

    # cannot do sudo <command> on laptop for next instruction
    if not linux_is_rpi():
        return

    lg.a('error: restarting BLE service')
    ble_mat_systemctl_restart_bluetooth()
