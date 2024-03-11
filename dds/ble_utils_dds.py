import json
import os
import pathlib
import shutil
import time

from dds.gps import gps_simulate_boat_speed
from dds.macs import dds_create_folder_macs_color
from dds.notifications import notify_ddh_error_hw_ble
from dds.timecache import its_time_to
from mat.ble.ble_mat_utils import ble_mat_get_bluez_version
from mat.utils import linux_is_rpi
from utils.ddh_config import dds_get_cfg_monitored_macs, dds_get_cfg_flag_purge_black_macs_on_boot, \
    ddh_get_cfg_gear_type, dds_get_cfg_moving_speed
from utils.ddh_shared import (
    send_ddh_udp_gui as _u,
    ddh_get_disabled_ble_flag_file,
    STATE_DDS_BLE_DISABLED,
    ddh_get_app_override_flag_file,
    STATE_DDS_BLE_APP_GPS_ERROR_SPEED,
    STATE_DDS_BLE_ANTENNA,
    dds_get_ddh_got_an_update_flag_file,
    STATE_DDS_SOFTWARE_UPDATED,
    get_ddh_folder_path_macs_black, STATE_DDS_BLE_HARDWARE_ERROR, get_ddh_folder_path_tweak,
    STATE_DDS_BLE_NO_ASSIGNED_LOGGERS,
)
from utils.logs import lg_dds as lg
import subprocess as sp


_g_ant_ble = "undefined"


def ble_show_monitored_macs():
    mm = dds_get_cfg_monitored_macs()
    for i in mm:
        lg.a("debug: monitored mac {}".format(i))


def ble_logger_ccx26x2r_needs_a_reset(mac):
    mac = mac.replace(':', '-')
    r = get_ddh_folder_path_tweak()

    # checks existence of 'tweak/<mac>.rst' file
    file_path = '{}/{}.rst'.format(r, mac)
    rv = os.path.exists(file_path)
    if rv:
        lg.a("debug: logger reset file {} found".format(file_path))
        os.unlink(file_path)
        lg.a("debug: logger reset file {} deleted".format(file_path))
    return rv


def ble_op_conditions_met(knots) -> bool:

    # when Bluetooth is disabled
    flag = ddh_get_disabled_ble_flag_file()
    if os.path.isfile(flag):
        _u(STATE_DDS_BLE_DISABLED)
        return False

    # when it is forced to work, ex: button 2 is pressed
    flag = ddh_get_app_override_flag_file()
    if os.path.isfile(flag):
        lg.a("debug: application override set")
        os.unlink(flag)
        return True

    # case: forgot to assign loggers
    if not dds_get_cfg_monitored_macs():
        _u(STATE_DDS_BLE_NO_ASSIGNED_LOGGERS)
        time.sleep(5)
        return False

    # when speed does not matter
    l_h = ddh_get_cfg_gear_type()
    speed_range = dds_get_cfg_moving_speed()
    if not l_h:
        # CASE: normal
        return True

    # CASE: trawling, we know for sure l_h is set here
    s_lo, s_hi = speed_range
    s_lo = float(s_lo)
    knots = float(knots)
    s_hi = float(s_hi)

    # simulation of boat speed, check if enabled
    s_lo, knots, s_hi = gps_simulate_boat_speed(s_lo, knots, s_hi)

    # check we are on valid moving range
    if s_lo <= knots <= s_hi:
        return True
    _u("{}/{}".format(STATE_DDS_BLE_APP_GPS_ERROR_SPEED, knots))


def ble_tell_gui_antenna_type(_h, desc):
    # from time to time
    s = "using {} antenna, adapter {}"
    if its_time_to(s, 60):
        _u(f"{STATE_DDS_BLE_ANTENNA}/BT_{desc}")

    # run this once
    if its_time_to('tell_gui_antenna_type', 3600):
        _ad = "hci{}".format(_h)
        s = s.format(desc, _ad)
        lg.a("-" * len(s))
        lg.a(s)
        lg.a("-" * len(s))


def ble_check_antenna_up_n_running(g, h: int):
    cr = "hciconfig hci{} | grep 'UP RUNNING'".format(h)
    rv = sp.run(cr, shell=True, stdout=sp.PIPE, stderr=sp.PIPE)
    if rv.returncode == 0:
        return True

    # will not be able to do next sudo <command> on laptop
    if not linux_is_rpi():
        return

    lg.a('warning: BLE interface hci{} seems down'.format(h))

    # only on rpi, try to recover it
    for c in [
        'sudo modprobe -r btusb',
        'sudo modprobe btusb',
        'sudo rfkill unblock bluetooth',
        'sudo systemctl restart hciuart',
        'sudo systemctl restart bluetooth',
        'sudo hciconfig hci{} up'.format(h)
    ]:
        sp.run('sleep 1', shell=True, stdout=sp.PIPE, stderr=sp.PIPE)
        rv = sp.run(c, shell=True, stdout=sp.PIPE, stderr=sp.PIPE)
        if rv.returncode:
            lg.a('command {} returned error {}'.format(c, rv.stderr))

    # checking again the state of the bluetooth interface
    time.sleep(1)
    rv = sp.run(cr, shell=True, stdout=sp.PIPE, stderr=sp.PIPE)
    if rv.returncode == 0:
        lg.a('success: we recovered BLE interface from down to up')
        return True

    # not UP and running, tell so
    e = "error: ble_check_antenna_up_n_running #{}".format(h)
    _u(STATE_DDS_BLE_HARDWARE_ERROR)
    time.sleep(5)
    if its_time_to(e, 600):
        lg.a(e.format(e))
        notify_ddh_error_hw_ble(g)


def dds_tell_software_update():
    # check for file created by DDH startup script
    # we may have uncommented the updater in such script
    f = dds_get_ddh_got_an_update_flag_file()
    if os.path.exists(f):
        os.unlink(f)
        lg.a("told software updated")
        # give GUI time and chances to show this
        _u(STATE_DDS_SOFTWARE_UPDATED)
        time.sleep(5)


def ble_apply_debug_hooks_at_boot():
    if dds_get_cfg_flag_purge_black_macs_on_boot():
        lg.a("debug: HOOK_PURGE_BLACK_MACS_ON_BOOT")
        p = pathlib.Path(get_ddh_folder_path_macs_black())
        shutil.rmtree(str(p), ignore_errors=True)
        dds_create_folder_macs_color()


def dds_check_bluez_version():
    v = ble_mat_get_bluez_version()
    if v != '5.66':
        lg.a("warning: --------------------")
        lg.a("warning: check bluez version")
        lg.a("warning: --------------------")


def dds_ble_init_rv_notes(d: dict):
    d["battery_level"] = 0xFFFF
    d["error"] = ""
    d["crit_error"] = 0
