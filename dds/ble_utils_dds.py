import os
import pathlib
import shutil
import time

from dds.macs import dds_create_folder_macs_color
from dds.sqs import sqs_msg_ddh_error_ble_hw
from dds.timecache import its_time_to
from mat.ble.ble_mat_utils import ble_mat_get_bluez_version
from mat.utils import linux_is_rpi
from utils.ddh_shared import (
    send_ddh_udp_gui as _u,
    ble_get_cc26x2_recipe_flags_from_json,
    dds_get_macs_from_json_file,
    ddh_get_disabled_ble_flag_file,
    STATE_DDS_BLE_DISABLED,
    ddh_get_app_override_flag_file,
    ddh_get_json_app_type,
    dds_get_json_moving_speed,
    STATE_DDS_BLE_APP_GPS_ERROR_SPEED,
    STATE_DDS_BLE_ANTENNA,
    dds_get_ddh_got_an_update_flag_file,
    STATE_DDS_SOFTWARE_UPDATED,
    get_ddh_folder_path_macs_black, STATE_DDS_BLE_HARDWARE_ERROR, get_ddh_folder_path_tweak,
)
from settings.ctx import hook_ble_purge_black_macs_on_boot
from utils.logs import lg_dds as lg
import subprocess as sp


_g_ant_ble = "undefined"


def ble_get_cc26x2_recipe_file_rerun_flag() -> int:
    rf = ble_get_cc26x2_recipe_flags_from_json()
    return rf["rerun"]


def ble_show_monitored_macs():
    mm = dds_get_macs_from_json_file()
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

    flag = ddh_get_disabled_ble_flag_file()
    if os.path.isfile(flag):
        _u(STATE_DDS_BLE_DISABLED)
        return False

    flag = ddh_get_app_override_flag_file()
    if os.path.isfile(flag):
        lg.a("debug: application override set")
        os.unlink(flag)
        return True

    l_h = ddh_get_json_app_type()
    speed_range = dds_get_json_moving_speed()

    # case: lobster trap, that is, no speed requirement
    if not l_h:
        return True

    # case: trawling
    s_lo, s_hi = speed_range
    s_lo = float(s_lo)
    knots = float(knots)
    s_hi = float(s_hi)
    valid_moving_range = s_lo <= knots <= s_hi
    if l_h and valid_moving_range:
        return True

    _u("{}/{}".format(STATE_DDS_BLE_APP_GPS_ERROR_SPEED, knots))


def ble_tell_gui_antenna_type(_h, desc):
    if desc == "internal":
        desc = "BT_internal"
    elif desc == "external":
        desc = "BT_external"

    global _g_ant_ble

    # from time to time
    s = "using {} antenna, adapter {}"
    if its_time_to(s, 60):
        _u("{}/{}".format(STATE_DDS_BLE_ANTENNA, desc))

    # we only ever run this function once
    if _g_ant_ble != "undefined":
        return

    # run this once
    _ad = "hci{}".format(_h)
    s = s.format(desc, _ad)
    lg.a("-" * len(s))
    lg.a(s)
    lg.a("-" * len(s))
    _g_ant_ble = desc


def ble_check_antenna_up_n_running(lat, lon, h: int):
    cr = "hciconfig hci{} | grep 'UP RUNNING'".format(h)
    rv = sp.run(cr, shell=True, stdout=sp.PIPE, stderr=sp.PIPE)
    if rv.returncode == 0:
        return True

    # will not be able to do next sudo <command> on laptop
    if not linux_is_rpi():
        return

    lg.a('warning: BLE interface hci{} seems down'.format(h))

    # try to recover it
    for c in [
        'sudo modprobe -r btusb',
        'sudo modprobe btusb',
        'sudo rfkill unblock bluetooth',
        'sudo systemctl restart hciuart',
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
    if its_time_to(e, 600):
        lg.a(e.format(e))
        sqs_msg_ddh_error_ble_hw(lat, lon)


def dds_tell_software_update():
    # check for file created by DDH startup script
    # we may have uncommented the updater in such script
    f = dds_get_ddh_got_an_update_flag_file()
    if os.path.exists(f):
        os.unlink(f)
        lg.a("told software updated")
        _u(STATE_DDS_SOFTWARE_UPDATED)
        # give GUI time to show this
        time.sleep(10)


def ble_apply_debug_hooks_at_boot():
    if hook_ble_purge_black_macs_on_boot:
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
