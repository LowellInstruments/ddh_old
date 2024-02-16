import datetime
import pathlib
import shutil
import time
from tzlocal import get_localzone
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
    notify_logger_error_retries
from dds.timecache import its_time_to
from mat.ble.ble_mat_utils import ble_mat_bluetoothctl_power_cycle, ble_mat_disconnect_all_devices_ll
from dds.ble_dl_rn4020 import ble_interact_rn4020
from dds.ble_dl_cc26x2r import ble_interact_cc26x2
from dds.gps import gps_tell_position_logger
from mat.utils import linux_is_rpi
from utils.ddh_config import dds_get_cfg_flag_purge_this_mac_dl_files_folder, dds_get_cfg_logger_sn_from_mac
from utils.ddh_shared import (
    send_ddh_udp_gui as _u,
    STATE_DDS_BLE_DOWNLOAD_OK,
    STATE_DDS_BLE_DOWNLOAD_ERROR,
    STATE_DDS_BLE_DOWNLOAD_WARNING,
    get_dl_folder_path_from_mac,
    STATE_DDS_BLE_DOWNLOAD, dds_get_aws_has_something_to_do_via_gui_flag_file,
    STATE_DDS_NOTIFY_HISTORY, STATE_DDS_BLE_ERROR_MOANA_PLUGIN, STATE_DDS_BLE_CONNECTING,
)
from utils.logs import lg_dds as lg
from dds.ble_dl_moana import ble_interact_moana


_g_logger_errors = {}


def _ble_analyze_logger_result(rv, mac, g, sn, err_critical):

    # success :)
    if rv == 0:
        rm_mac_black(mac)
        rm_mac_orange(mac)
        add_mac_black(mac)
        notify_logger_download(g, mac)
        if mac in _g_logger_errors.keys():
            del _g_logger_errors[mac]
        lg.a("OK! logger {}/{}".format(mac, sn))
        _u(f"{STATE_DDS_BLE_DOWNLOAD_OK}/{sn}")
        time.sleep(1)
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
        _g_logger_errors[mac] = 10

    if _g_logger_errors[mac] >= 10:
        rm_mac_orange(mac)
        add_mac_black(mac)
        e = "error: logger {}/{} totally failed, critical = {}"
        lg.a(e.format(mac, sn, err_critical))
        _u(f"{STATE_DDS_BLE_DOWNLOAD_ERROR}/{sn}")
        notify_logger_error_retries(g, mac)
        _g_logger_errors[mac] = 0

    else:
        rm_mac_orange(mac)
        add_mac_orange(mac)
        lg.a("warning: logger {}/{} NOT done".format(mac, sn))
        _u(f"{STATE_DDS_BLE_DOWNLOAD_WARNING}/{sn}")


def _ble_logger_is_cc26x2r(info: str):
    return "DO-" in info


def _ble_logger_is_tdo(info: str):
    return "TAP" in info or "TDO" in info


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
        return

    # allows discarding loggers faster
    _crit_error = False
    _error_dl = ""

    # some GUI update
    _u(f"{STATE_DDS_BLE_CONNECTING}/{sn}")

    # --------------------
    # logger interaction
    # --------------------
    if _ble_logger_is_cc26x2r(info):
        rv, notes = await ble_interact_cc26x2(mac, info, g, hs)
        _crit_error = notes["crit_error"]
        _error_dl = notes["error"]

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
            return

    elif _ble_logger_is_tdo(info):
        rv, notes = await ble_interact_tdo(mac, info, g, hs)
        _crit_error = notes["crit_error"]
        _error_dl = notes["error"]

    else:
        lg.a(f'error: this should not happen, info {info}')
        return

    # tell GUI how it went, also do MAC colors stuff
    _ble_analyze_logger_result(rv, mac, g, sn, _crit_error)

    # on GUI, all times are local, not UTC
    tz_ddh = get_localzone()
    tz_utc = datetime.timezone.utc
    dt_local = dt.replace(tzinfo=tz_utc).astimezone(tz=tz_ddh)

    # ------------------------------------
    # so GUI can update its HISTORY tab
    # ------------------------------------
    epoch = int(dt_local.timestamp())
    s = "{}/add&{}&{}&{}&{}&{}"
    e = 'ok' if not rv else _error_dl
    _u(s.format(STATE_DDS_NOTIFY_HISTORY, mac, e, lat, lon, epoch))

    # on error, some sort of restart bluetooth
    if rv:
        # for RPi
        ble_mat_bluetoothctl_power_cycle()
        # for laptop
        if not linux_is_rpi():
            ble_mat_disconnect_all_devices_ll()

    # only sync AWS when NOT on development machine
    if not linux_is_rpi():
        return

    # AWS flag checked later, after ALL loggers download
    try:
        if not rv:
            flag = dds_get_aws_has_something_to_do_via_gui_flag_file()
            pathlib.Path(flag).touch()
            lg.a("created AWS flag file")
    except (Exception, ):
        lg.a('error: creating AWS flag file')


async def ble_interact_all_loggers(macs_det, macs_mon, g, _h: int, _h_desc):

    for mac, model in macs_det.items():
        # because macs_det, macs_mon macs_mon are lowercase
        mac = mac.lower()
        if mac not in macs_mon:
            continue

        # helps in distance-detection issues
        if its_time_to(f'tell_saw_mac_{mac}', 1800):
            sn = dds_get_cfg_logger_sn_from_mac(mac)
            lg.a(f"debug: logger {sn} / mac {mac} seen, it's been a while")

        if is_mac_in_black(mac):
            continue
        if is_mac_in_orange(mac):
            continue

        # show the position of the logger we will download
        gps_tell_position_logger(g)

        # MAC passed all filters, work with it
        await _ble_id_n_interact_logger(mac, model, _h, g)
