import datetime
import json
import os
import pathlib
import shutil
import time

import requests
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
from dds.timecache import its_time_to
from mat.ble.ble_mat_utils import (ble_mat_get_antenna_type,
                                   ble_mat_systemctl_restart_bluetooth)
from dds.ble_dl_rn4020 import ble_interact_rn4020
from dds.ble_dl_dox import ble_interact_do1_or_do2
from dds.gps import gps_tell_position_logger
from mat.data_converter import default_parameters, DataConverter
from mat.lix import id_lid_file_flavor, LID_FILE_V2, convert_lix_file, LID_FILE_V1
from mat.lix_dox import is_a_do2_file
from mat.utils import linux_is_rpi
from utils.ddh_config import (dds_get_cfg_flag_purge_this_mac_dl_files_folder,
                              dds_get_cfg_logger_sn_from_mac, dds_get_cfg_logger_mac_from_sn)
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


def _ble_detect_hypoxia(f_lid, bat, g):
    # todo ---> test this
    try:
        if not f_lid.endswith('.lid') or not is_a_do2_file(f_lid):
            return
        f_csv = f_lid.replace('.lid', '_DissolvedOxygen.csv')
        if not os.path.exists(f_csv):
            return
        # f_csv: 2404725_lab_20240407_230609.csv
        sn = os.path.basename(f_csv).split('_')[0]
        mac = dds_get_cfg_logger_mac_from_sn()
        ln = LoggerNotification(mac, sn, 'DOX', bat)
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


def _ble_convert_lid(d):
    ls_lid = d['dl_files']
    bat = d['battery_level']
    g = d['gps']

    for f in ls_lid:
        # f: absolute file path ending in .lid
        n = id_lid_file_flavor(f)
        lg.a(f"after download converting LID file v{n} {f}")
        if n == LID_FILE_V2:
            convert_lix_file(f)
            _ble_detect_hypoxia(f, bat, g)
        if n == LID_FILE_V1:
            # do the old MAT library conversion
            parameters = default_parameters()
            DataConverter(f, parameters).convert()
        lg.a(f"OK: after download converted LID file v{n} {f}")


# def _ble_convert_cst(d):
#     ls_lid = d['dl_files']
#     ls_csv = [i.replace('.lid', '.csv') for i in ls_lid]
#
#     port_ddb = 8001
#     for f_csv in ls_csv:
#         # todo: test what happen if DDB not running, timeout?
#         f_cst = f_csv.replace('.csv', '.cst')
#         with open(f_csv, 'r') as fv:
#             with open(f_cst, 'w') as ft:
#                 for i, s in enumerate(fv.readline()):
#                     if i == 0:
#                         ft.write('lat,lon,' + s)
#                     else:
#                         dt_s = s.split(',')
#                         print(dt_s)
#                         # format pepi
#                         dt_s = 'pepi'
#                         url = f'http://0.0.0.0:{port_ddb}/ddb/gpq?dt_s={dt_s}'
#                         try:
#                             rsp = requests.get(url, timeout=.1)
#                             rsp.raise_for_status()
#                             # rsp: b'{"gpq_get":0,"rv":"(1, 5.0, (\'2024...', (\'lat1\', \'lon1\')))"}'
#                             rv = json.loads(rsp.text)['rv'] if rsp else None
#                             index, diff, candidate = rv
#                             print('candidate', candidate)
#                         except (Exception,) as ex:
#                             print(f'create CST file error {ex}')


def _ble_convert_cst(f_csv):
    port_ddb = 8001
    f_cst = f_csv.replace('.csv', '.cst')
    url = 'http://0.0.0.0:8001/ddb/gpq?dt_s='

    # read CSV file
    with open(f_csv, 'r') as fv:
        ll_fv = fv.readlines()

    # write CST file
    with open(f_cst, 'w') as ft:
        for i, s in enumerate(ll_fv):
            if i == 0:
                print(f'debug: file {f_csv} has {len(ll_fv)} lines')
                ft.write('lat,lon,' + s)
                continue

            # dt_s: 2024-04-04T13:45:31.000
            # dt_s=20240102030405&'
            dt_s = s.split(',')[0].replace('.000', '')
            dt_s = ''.join(c for c in dt_s if c.isdigit())
            try:
                rsp = requests.get(url+dt_s, timeout=.1)
                rsp.raise_for_status()
                # rsp: b'{"gpq_get":0,"rv":"(1, 5.0, (\'2024...', (\'lat1\', \'lon1\')))"}'
                # ctx = json.loads(rsp.text)['rv'] if rsp else None
                ctx = json.loads(rsp.text)['rv']
                # ctx: (1, 8073686.0, ('2024/01/02 03:04:05', ('lat1', 'lon1')))
                if ctx:
                    index, diff, t_lat_lon = ctx
                    t, latlon = t_lat_lon
                    lat, lon = latlon
                    ft.write(f'{lat},{lon},' + s)
                else:
                    ft.write(f',,' + s)
            except (Exception,) as ex:
                print(f'create CST file error {ex}')
                break


if __name__ == '__main__':
    f_csv = '/home/kaz/PycharmProjects/ddh/dl_files/f0-5e-cd-25-95-e7/2402770_BIL_20240404_134531_TDO.csv'
    _ble_convert_cst(f_csv)



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
        notes['gps'] = g
        _crit_error = notes["crit_error"]
        _error_dl = notes["error"]
        _ble_convert_lid(notes)
        #_ble_convert_cst(notes)

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
        notes['gps'] = g
        _crit_error = notes["crit_error"]
        _error_dl = notes["error"]
        _ble_convert_lid(notes)
        #_ble_convert_cst(notes)

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

    # ------------------------------------------------
    # ensure value for error_dl, not always populated
    # ------------------------------------------------
    if not _error_dl:
        _error_dl = 'comm. error'
    ln = LoggerNotification(mac, sn, info, bat)
    _ble_analyze_logger_result(rv, g, ln, _crit_error)

    # ------------------------------------
    # so GUI can update its HISTORY tab
    # ------------------------------------
    ep_loc = int(dt_local.timestamp())
    ep_utc = int(dt.timestamp())
    e = 'ok' if not rv else _error_dl

    _u(f"{STATE_DDS_NOTIFY_HISTORY}/add&"
       f"{mac}&{e}&{lat}&{lon}&{ep_loc}&{ep_utc}")


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
