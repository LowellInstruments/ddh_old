#!/usr/bin/env python3
import multiprocessing
import pathlib
import subprocess as sp
import os
import sys
import time

from bullet import Bullet

from scripts.script_test_box_buttons import main_test_box_buttons
from scripts.script_test_gps_quectel import main_test_gps_quectel
from utils.tmp_paths import (
    LI_PATH_EMOLT_FILE_FLAG,
    LI_PATH_GROUPED_S3_FILE_FLAG,
    LI_PATH_DDH_GPS_EXTERNAL,
    TMP_PATH_GPS_DUMMY, TMP_PATH_GRAPH_TEST_MODE_JSON)


def sh(c):
    print('\nshell -> ', c)
    rv = sp.run(c, shell=True, stdout=sp.PIPE, stderr=sp.PIPE)
    print('ou', rv.stdout)
    print('er', rv.stderr)
    return rv.returncode


def is_rpi():
    return sh('cat /proc/cpuinfo | grep aspberry') == 0


def cb_view_current_flags():

    # assume crontab off
    cf = '/etc/crontab'
    s1, s2 = 'crontab_ddh.sh', 'crontab_api.sh'
    ct_ddh, ct_api = 0, 0
    if sh(f'grep -q {s1} {cf}') == 0:
        # line present, check if commented or not
        ct_ddh = 0 if sh(f"grep {s1} {cf} | grep -F '#' > /dev/null") == 0 else 1
    if sh(f'grep -q {s2} {cf}') == 0:
        ct_api = 0 if sh(f"grep {s2} {cf} | grep -F '#' > /dev/null") == 0 else 1

    print('emolt       =', os.path.exists(LI_PATH_EMOLT_FILE_FLAG))
    print('aws group   =', os.path.exists(LI_PATH_GROUPED_S3_FILE_FLAG))
    print('gps puck    =', os.path.exists(LI_PATH_DDH_GPS_EXTERNAL))
    print('gps dummy   =', os.path.exists(TMP_PATH_GPS_DUMMY))
    print('graph test  =', os.path.exists(TMP_PATH_GRAPH_TEST_MODE_JSON))
    print('crontab_ddh =', ct_ddh)
    print('crontab_api =', ct_api)


def cb_kill_ddh():
    for c in (
            'killall main_ddh',
            'killall main_dds',
            'killall main_ddh_controller',
            'killall main_dds_controller'
    ):
        sh(c)


def cb_toggle_emolt_marker():
    p = LI_PATH_EMOLT_FILE_FLAG if is_rpi() else '/tmp/emolt'
    os.unlink(p) if os.path.exists(p) else pathlib.Path(p).touch()


def cb_toggle_aws_s3_group():
    p = LI_PATH_GROUPED_S3_FILE_FLAG if is_rpi() else '/tmp/aws_s3_group'
    os.unlink(p) if os.path.exists(p) else pathlib.Path(p).touch()


def cb_toggle_gps_external():
    p = LI_PATH_DDH_GPS_EXTERNAL if is_rpi() else '/tmp/gps_external'
    os.unlink(p) if os.path.exists(p) else pathlib.Path(p).touch()


def cb_toggle_gps_dummy():
    p = TMP_PATH_GPS_DUMMY if is_rpi() else '/tmp/gps_dummy'
    os.unlink(p) if os.path.exists(p) else pathlib.Path(p).touch()


def cb_toggle_graph_test_mode():
    p = TMP_PATH_GRAPH_TEST_MODE_JSON if is_rpi() else '/tmp/graph_test_mode'
    os.unlink(p) if os.path.exists(p) else pathlib.Path(p).touch()


def _toggle_crontab(s):
    cf = '/etc/crontab'
    cf_run = f'/home/pi/li/ddt/_dt_files/crontab_{s}.sh'
    if sh(f'grep -q crontab_{s}.sh {cf}') == 1:
        # no string found in whole crontab, add it
        sh('echo -e "* * * * * pi {cf_run}\n" | sudo tee -a $CF')
        print(f"added {s} to {cf}")
        return

    # line is there, it is commented?
    rv = sh(f"grep crontab_{s}.sh {cf} | grep -F '#' > /dev/null")

    # delete any lines containing "crontab_ddh.sh"
    sh(f"sudo sed -i '/crontab_{s}/d' {cf}")

    if rv == 0:
        print(f"crontab {s} was OFF, enabling it")
        sh(f'echo "* * * * * pi {cf_run}" | sudo tee -a {cf}')
    else:
        print(f"crontab {s} was ON, disabling it")
        sh(f'echo "#* * * * * pi {cf_run}" | sudo tee -a {cf}')

    # restart the cron service
    sh("sudo systemctl restart cron.service")
    print("crontab service restarted")


def cb_toggle_crontab_ddh():
    return _toggle_crontab('ddh')


def cb_toggle_crontab_api():
    return _toggle_crontab('api')


def cb_run_script_gps_test():
    main_test_gps_quectel()


def cb_run_script_buttons_test():
    main_test_box_buttons()


def cb_quit():
    print('quitting DDC')
    sys.exit(0)


op = {
    "view current flags": cb_view_current_flags,
    "kill ddh": cb_kill_ddh,
    "toggle emolt marker": cb_toggle_emolt_marker,
    "toggle AWS s3 group": cb_toggle_aws_s3_group,
    "toggle GPS external": cb_toggle_gps_external,
    "toggle GPS dummy": cb_toggle_gps_dummy,
    "toggle crontab DDH": cb_toggle_crontab_ddh,
    "toggle crontab API": cb_toggle_crontab_api,
    "toggle graph test mode": cb_toggle_graph_test_mode,
    "test GPS Quectel": cb_run_script_gps_test,
    "test box buttons": cb_run_script_buttons_test,
    "quit": cb_quit,
}


def main_ddc():
    while 1:
        os.system('clear')

        menu = Bullet(
            prompt="\nChoose what to run:",
            choices=list(op.keys()),
            indent=0,
            align=5,
            margin=2,
            shift=0,
            bullet="->",
            pad_right=5,
            return_index=True
        )

        # _: text, i: index
        txt, i = menu.launch()

        # run the callbacks
        cb = list(op.values())[i]

        if txt == 'quit':
            break

        p = multiprocessing.Process(target=cb)
        p.start()
        p.join()

        # wait some time
        time.sleep(3)
