#!/usr/bin/env python3
import multiprocessing
import pathlib
import subprocess as sp
import os
import sys

from bullet import Bullet

from utils.tmp_paths import (
    LI_PATH_EMOLT_FILE_FLAG,
    LI_PATH_GROUPED_S3_FILE_FLAG,
    LI_PATH_DDH_GPS_EXTERNAL,
    TMP_PATH_GPS_DUMMY, TMP_PATH_GRAPH_TEST_MODE_JSON)


def sh(c):
    print('\nshell -> ', c)
    rv = sp.run(c, shell=True, stdout=sp.PIPE, stderr=sp.PIPE)
    return rv.returncode


def is_rpi():
    return sh('cat /proc/cpuinfo | grep aspberry') == 0


def cb_view_current_flags():
    pass


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


def _run_script(s):
    v = '/home/pi/li/venv/bin'
    c = f'source {v}/activate && '
    c += 'cd /home/pi/li/ddh/scripts && '
    c += f'./run_script_{s}.sh'
    sh(c)


def cb_run_script_do_logger():
    pass


def cb_run_script_gps_test():
    return _run_script('gps_test')


def cb_run_script_buttons_test():
    return _run_script('buttons_test')


def cb_quit():
    print('quitting DDC')
    sys.exit(0)


op = {
    "view current flags": cb_view_current_flags,
    "kill ddh": cb_kill_ddh,
    "toggle emolt marker": cb_toggle_emolt_marker,
    "toggle AWS s3 group": cb_toggle_aws_s3_group,
    "toggle GPS external": cb_toggle_gps_external,
    "toggle crontab DDH": cb_toggle_crontab_ddh,
    "toggle crontab API": cb_toggle_crontab_api,
    "toggle graph test mode": cb_toggle_graph_test_mode,
    "run script deploy DO-X logger": cb_run_script_do_logger,
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
        _, i = menu.launch()

        # run the callbacks
        list(op.values())[i]()
