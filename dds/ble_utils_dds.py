import os
import pathlib
import shutil
import time

from dds.macs import dds_create_folder_macs_color
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
    get_ddh_folder_path_macs_black,
)
from settings.ctx import hook_ble_purge_black_macs_on_boot
from utils.logs import lg_dds as lg


_g_ant_ble = "undefined"


def ble_get_cc26x2_recipe_file_rerun_flag() -> int:
    rf = ble_get_cc26x2_recipe_flags_from_json()
    return rf["rerun"]


def ble_show_monitored_macs():
    mm = dds_get_macs_from_json_file()
    for i in mm:
        lg.a("debug: monitored mac {}".format(i))


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

    # case: lobster trap, no speed requirement
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
    if _g_ant_ble == "undefined" or _g_ant_ble != desc:
        _ad = "hci{}".format(_h)
        s = "using {} antenna, adapter {}".format(desc, _ad)
        lg.a("-" * len(s))
        lg.a(s)
        lg.a("-" * len(s))
        _u("{}/{}".format(STATE_DDS_BLE_ANTENNA, desc))
    _g_ant_ble = desc


def dds_tell_software_update():
    # check for file created by DDH startup script
    f = dds_get_ddh_got_an_update_flag_file()
    if os.path.exists(f):
        # don't unlink(f) we want updates only once x boot (/tmp)
        lg.a("told software updated")
        _u(STATE_DDS_SOFTWARE_UPDATED)
        # give GUI time to show this
        time.sleep(5)


def ble_apply_debug_hooks_at_boot():
    if hook_ble_purge_black_macs_on_boot:
        lg.a("debug: HOOK_PURGE_BLACK_MACS_ON_BOOT")
        p = pathlib.Path(get_ddh_folder_path_macs_black())
        shutil.rmtree(str(p), ignore_errors=True)
        dds_create_folder_macs_color()
