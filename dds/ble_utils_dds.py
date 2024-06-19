import json
import os
import pathlib
import shutil
import time
import threading
from signal import pause

from gpiozero import Button

from dds.gps import gps_simulate_boat_speed
from dds.in_ports_geo import dds_ask_in_port_to_ddn
from dds.macs import dds_create_folder_macs_color
from dds.notifications import notify_ddh_error_hw_ble
from dds.timecache import is_it_time_to
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
    STATE_DDS_BLE_NO_ASSIGNED_LOGGERS, STATE_DDS_PRESSED_BUTTON_2, STATE_DDS_BLE_SCAN, STATE_DDS_GPS_IN_PORT,
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


def ble_op_conditions_met(g) -> bool:

    lat, lon, tg, knots = g

    # when Bluetooth is disabled
    flag = ddh_get_disabled_ble_flag_file()
    if os.path.isfile(flag):
        _u(STATE_DDS_BLE_DISABLED)
        return False

    # are we forced to work
    flag = ddh_get_app_override_flag_file()

    # are we in port
    are_we_in_port = dds_ask_in_port_to_ddn(g)
    if are_we_in_port and not os.path.isfile(flag):
        _u(STATE_DDS_GPS_IN_PORT)
        return False

    # seems we are going to work
    _u(STATE_DDS_BLE_SCAN)

    # when it is forced to work, ex: button 2 is pressed
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
        # fixed gear case
        return True

    # CASE: trawling, we know for sure l_h is set here
    s_lo, s_hi = speed_range
    s_lo = float(s_lo)
    knots = float(knots)
    s_hi = float(s_hi)

    # simulation of boat speed
    s_lo, knots, s_hi = gps_simulate_boat_speed(s_lo, knots, s_hi)

    # check we are on valid moving range
    if s_lo <= knots <= s_hi:
        return True
    _u(f"{STATE_DDS_BLE_APP_GPS_ERROR_SPEED}/{knots}")


def ble_tell_gui_antenna_type(_h, desc):
    # from time to time
    _ad = f"hci{_h}"
    s = f"using {desc} antenna, adapter {_ad}"
    if is_it_time_to(s, 60):
        _u(f"{STATE_DDS_BLE_ANTENNA}/{desc} radio")

    # run this once
    if is_it_time_to('tell_gui_antenna_type', 3600):
        lg.a('\n')
        lg.a('-----------------------')
        lg.a(s)
        lg.a('-----------------------\n')


def ble_check_antenna_up_n_running(g, h: int):
    cr = f"hciconfig hci{h} | grep 'UP RUNNING'"
    rv = sp.run(cr, shell=True, stdout=sp.PIPE, stderr=sp.PIPE)
    if rv.returncode == 0:
        return True

    # will not be able to do next sudo <command> on laptop
    if not linux_is_rpi():
        return

    lg.a(f'warning: BLE interface hci{h} seems down')

    # only on rpi, try to recover it
    for c in [
        'sudo modprobe -r btusb',
        'sudo modprobe btusb',
        'sudo rfkill unblock bluetooth',
        'sudo systemctl restart hciuart',
        'sudo systemctl restart bluetooth',
        f'sudo hciconfig hci{h} up'
    ]:
        sp.run('sleep 1', shell=True)
        rv = sp.run(c, shell=True, stdout=sp.PIPE, stderr=sp.PIPE)
        if rv.returncode:
            lg.a(f'error: command {c} returned error {rv.stderr}')

    # checking again the state of the bluetooth interface
    time.sleep(1)
    rv = sp.run(cr, shell=True, stdout=sp.PIPE, stderr=sp.PIPE)
    if rv.returncode == 0:
        lg.a('success: we recovered BLE interface from down to up')
        return True

    # not UP and running, tell so
    e = f"error: ble_check_antenna_up_n_running #{h}"
    _u(STATE_DDS_BLE_HARDWARE_ERROR)
    time.sleep(5)
    if is_it_time_to(e, 600):
        lg.a(e.format(e))
        notify_ddh_error_hw_ble(g)


def _th_gpio_box_buttons():
    if not linux_is_rpi():
        return

    def button1_pressed_cb():
        pass

    def button2_pressed_cb():
        _u(STATE_DDS_PRESSED_BUTTON_2)

    def button3_pressed_cb():
        pass

    b1 = Button(16, pull_up=True, bounce_time=0.1)
    b2 = Button(20, pull_up=True, bounce_time=0.1)
    b3 = Button(21, pull_up=True, bounce_time=0.1)
    b1.when_pressed = button1_pressed_cb
    b2.when_pressed = button2_pressed_cb
    b3.when_pressed = button3_pressed_cb

    pause()


def dds_create_buttons_thread():
    bth = threading.Thread(target=_th_gpio_box_buttons)
    bth.start()


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
    d["dl_files"] = []
    d["rerun"] = False
