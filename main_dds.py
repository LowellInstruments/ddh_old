#!/usr/bin/env python3

import json
import os
import sys
from multiprocessing import Process
import time
import subprocess as sp
from ddh.draw_graph import gfm_serve
from dds.aws import aws_sync_or_cp
from dds.ble import (
    ble_interact_all_loggers,
    ble_show_antenna_type,
    ble_check_antenna_up_n_running,
    ble_op_conditions_met,
    ble_show_monitored_macs
)
from dds.ble_scan import ble_scan
from dds.cnv import cnv_serve
from dds.gpq import GpqW
from dds.hooks import apply_debug_hooks
from dds.macs import (
    dds_create_folder_macs_color,
    dds_macs_color_show_at_boot
)
from dds.net import net_serve
from dds.notifications_v2 import (
    notify_boot,
    notify_error_sw_crash,
    notify_ddh_needs_sw_update,
    notify_ddh_alive,
    notify_error_gps_clock_sync
)
from dds.sqs import (
    dds_create_folder_sqs,
    sqs_serve,
)
from dds.lef import lef_create_folder
from dds.buttons import (
    dds_create_buttons_thread,
)
from dds.state import ddh_state
from dds.timecache import is_it_time_to
from mat.linux import (
    linux_app_write_pid_to_tmp,
    linux_is_process_running
)
from mat.ble.ble_mat_utils import (
    ble_mat_disconnect_all_devices_ll,
    ble_mat_get_antenna_type_v2,
    ble_mat_get_bluez_version
)
from mat.utils import linux_is_rpi
from utils.ddh_config import (
    dds_check_cfg_has_box_info,
    dds_get_cfg_monitored_macs,
    dds_check_config_file,
    dds_get_cfg_flag_download_test_mode,
)
from utils.ddh_shared import (
    PID_FILE_DDS,
    dds_create_folder_dl_files,
    dds_create_folder_logs,
    dds_ensure_proper_working_folder,
    PID_FILE_DDS_CONTROLLER,
    NAME_EXE_DDS_CONTROLLER,
    NAME_EXE_DDS,
    ael,
    dds_create_folder_gpq,
    NAME_EXE_BRT,
    dds_get_ddh_got_an_update_flag_file,
    STATE_DDS_SOFTWARE_UPDATED,
)
from utils.logs import (
    lg_dds as lg,
    dds_log_tracking_add,
    dds_log_core_start_at_boot
)
import setproctitle
from utils.ddh_shared import send_ddh_udp_gui as _u
from utils.flag_paths import TMP_PATH_BLE_IFACE
from dds.gps_measure import (
    gps_utils_boot_wait_long,
    gps_know_hat_firmware_version,
    gps_measure
)
from dds.gps_utils import (
    gps_utils_clock_sync_if_so,
    gps_utils_banner_clock_sync_at_boot,
    gps_utils_did_we_ever_clock_sync,
    gps_utils_tell_vessel_name,
    gps_utils_parse_errors, gps_utils_show_gps_clock_sync
)

# to write to temporary GPS database
_g_gpw = GpqW()


def main_dds():

    rv = dds_check_config_file()
    if rv:
        _u(f"bad_conf/{rv}")
        os._exit(1)

    dds_create_buttons_thread()
    dds_tell_software_was_just_updated()
    dds_check_cfg_has_box_info()
    dds_ensure_proper_working_folder()
    dds_create_folder_macs_color()
    dds_create_folder_sqs()
    lef_create_folder()
    dds_create_folder_gpq()
    dds_create_folder_dl_files()
    dds_create_folder_logs()
    dds_log_core_start_at_boot()
    dds_macs_color_show_at_boot()
    m_j = dds_get_cfg_monitored_macs()
    dds_check_bluez_version()

    ble_show_monitored_macs()
    apply_debug_hooks()
    ble_mat_disconnect_all_devices_ll()

    # seems boot process is going well
    setproctitle.setproctitle(NAME_EXE_DDS)
    linux_app_write_pid_to_tmp(PID_FILE_DDS)

    # GPS boot stage, can take from seconds to minutes
    gps_know_hat_firmware_version()
    gps_utils_boot_wait_long()

    # show message we are going to try GPS clock sync at boot
    gps_utils_banner_clock_sync_at_boot()

    # GPS clock sync at boot, remain here until successful
    _skip_notification_gps_sync_boot_error = 1
    while not gps_utils_did_we_ever_clock_sync():
        g = gps_measure()
        if g:
            lat, lon, tg, speed = g
            if gps_utils_clock_sync_if_so(tg):
                gps_utils_show_gps_clock_sync()
                notify_boot(g)
                break
        if is_it_time_to('report_gps_sync_boot_error', 1800):
            if _skip_notification_gps_sync_boot_error == 0:
                lg.a('error: cannot GPS sync at boot, sending notification')
                notify_error_gps_clock_sync()
                sqs_serve()
            else:
                _skip_notification_gps_sync_boot_error = 0

    # -------------------------------------------------------------------
    # select BLE antenna, do here to have time to get up from run_dds.sh
    # -------------------------------------------------------------------
    h, h_d = ble_mat_get_antenna_type_v2()

    # save which BLE interface we use, API needs it
    try:
        with open(TMP_PATH_BLE_IFACE, "w") as f:
            json.dump({"ble_iface_used": h_d}, f)
    except (Exception, ) as ex:
        lg.a(f'error: saving {TMP_PATH_BLE_IFACE} -> {ex}')

    if notify_ddh_needs_sw_update(g):
        s = 'warning: this DDH needs an update'
        lg.a('-' * len(s))
        lg.a(s)
        lg.a('-' * len(s))

    if dds_get_cfg_flag_download_test_mode():
        lg.a('detected DDH download test mode')

    # =============
    # main loop
    # =============
    while 1:

        # tell GUI
        gps_utils_tell_vessel_name()

        # other stages
        # cst_serve()
        gfm_serve()
        cnv_serve()
        aws_sync_or_cp()
        sqs_serve()
        net_serve()

        # GPS stage
        g = gps_measure()
        if gps_utils_parse_errors(g):
            time.sleep(1)
            continue

        # we have a good GPS frame
        lat, lon, tg, speed = g
        dds_log_tracking_add(lat, lon, tg)
        gps_utils_clock_sync_if_so(tg)

        # send SQS ping
        notify_ddh_alive(g)

        # check we do Bluetooth or not
        ble_show_antenna_type(h, h_d)
        if not ble_check_antenna_up_n_running(g, h):
            # note: ensure 'hciconfig' command is installed
            continue

        # check operation conditions are met
        if not ble_op_conditions_met(g):
            continue

        # moving this here allows for way lighter GPQ files
        _g_gpw.add(tg, lat, lon)

        # poor semaphore
        ddh_state.state_set_downloading_ble()

        # BLE scan stage
        args = [m_j, g, h, h_d]
        det = ael.run_until_complete(ble_scan(*args))

        # BLE download stage
        args = [det, m_j, g, h, h_d]
        rvi = ael.run_until_complete(ble_interact_all_loggers(*args))

        # poor semaphore
        ddh_state.state_clr_downloading_ble()

        # recovery situations
        if rvi:
            lg.a("warning: disconnect all BLE devices due to error, set ble_reset_req")
            ble_mat_disconnect_all_devices_ll()
            ddh_state.state_set_ble_reset_req()


def dds_tell_software_was_just_updated():
    f = dds_get_ddh_got_an_update_flag_file()
    if os.path.exists(f):
        os.unlink(f)
        lg.a("told software updated")
        # give GUI time and chances to show this
        _u(STATE_DDS_SOFTWARE_UPDATED)
        time.sleep(5)


def dds_check_bluez_version():
    v = ble_mat_get_bluez_version()
    if v != '5.66':
        lg.a("warning: --------------------------")
        lg.a(f"warning: bluez version {v} != 5.66")
        lg.a("warning: --------------------------")


def _alarm_dds_crash(n):
    if n == 0:
        return
    lg.a(f'error: _alarm_dds_crash, n = {n}')
    if is_it_time_to('tell_dds_child_crash', 300):
        notify_error_sw_crash()


def controller_main_dds():

    # don't run DDS when BRT range tool is running
    if linux_is_process_running(NAME_EXE_BRT):
        print('brt running, ddh should not')
        return

    # prepare to launch DDH child
    s = NAME_EXE_DDS_CONTROLLER
    p = PID_FILE_DDS_CONTROLLER
    setproctitle.setproctitle(s)
    linux_app_write_pid_to_tmp(p)
    lg.a(f"=== {s} started ===")

    # kill any old son
    ne = NAME_EXE_DDS
    c = (f'(ps -aux | grep -w {ne} | grep -v grep) '
         f'&& echo "kill loose DDS" && killall {ne} && sleep 3')
    sp.run(c, shell=True)

    while 1:
        # GUI KILLs this process when desired
        lg.a(f"=== {s} launching child ===")
        p = Process(target=main_dds)
        p.start()
        p.join()
        _alarm_dds_crash(p.exitcode)
        lg.a(f"=== {s} waits child, exitcode {p.exitcode} ===")
        time.sleep(5)


if __name__ == "__main__":

    if not linux_is_rpi():
        # debug: run without DDS controller
        main_dds()
        sys.exit(0)

    if not linux_is_process_running(NAME_EXE_DDS_CONTROLLER):
        controller_main_dds()
    else:
        print(f"not launching {NAME_EXE_DDS_CONTROLLER}, already running at python level")
