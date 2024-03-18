#!/usr/bin/env python3


import multiprocessing
import pathlib
import subprocess as sp
import sys
import time
from os.path import exists
from os import unlink
from os import system
from bullet import Bullet

from scripts.script_provision import provision_ddh
from utils.tmp_paths import (
    LI_PATH_EMOLT_FILE_FLAG,
    LI_PATH_GROUPED_S3_FILE_FLAG,
    LI_PATH_DDH_GPS_EXTERNAL,
    TMP_PATH_GPS_DUMMY, TMP_PATH_GRAPH_TEST_MODE_JSON)

g_fem = 0
g_fag = 0
g_fge = 0
g_fgd = 0
g_fgt = 0
g_fcd = 0
g_fca = 0


def _p(s):
    print(s)


def sh(c):
    rv = sp.run(c, shell=True, stdout=sp.PIPE, stderr=sp.PIPE)
    return rv.returncode


def is_rpi():
    return sh('cat /proc/cpuinfo | grep aspberry') == 0


def cb_get_current_flags():

    # will use global vars
    global g_fem
    global g_fag
    global g_fge
    global g_fgd
    global g_fgt
    global g_fcd
    global g_fca

    # assume crontab off
    cf = '/etc/crontab'
    s1, s2 = 'crontab_ddh.sh', 'crontab_api.sh'
    if sh(f'grep -q {s1} {cf}') == 0:
        # line present, check if commented or not
        g_fcd = 0 if sh(f"grep {s1} {cf} | grep -F '#' > /dev/null") == 0 else 1
    if sh(f'grep -q {s2} {cf}') == 0:
        g_fca = 0 if sh(f"grep {s2} {cf} | grep -F '#' > /dev/null") == 0 else 1

    g_fem = int(exists(LI_PATH_EMOLT_FILE_FLAG))
    g_fag = int(exists(LI_PATH_GROUPED_S3_FILE_FLAG))
    g_fge = int(exists(LI_PATH_DDH_GPS_EXTERNAL))
    g_fgd = int(exists(TMP_PATH_GPS_DUMMY))
    g_fgt = int(exists(TMP_PATH_GRAPH_TEST_MODE_JSON))


def cb_kill_ddh():
    for c in (
            'killall main_ddh',
            'killall main_dds',
            'killall main_ddh_controller',
            'killall main_dds_controller'
    ):
        sh(c)
    _p('sent kill signal to DDH software')
    time.sleep(2)


def cb_kill_lxpanel():
    c = 'lxpanelctl restart'
    sh(c)
    _p('sent kill signal to lxpanel')
    _p('note: only works in graphical session')
    time.sleep(2)


def cb_toggle_emolt_marker():
    p = LI_PATH_EMOLT_FILE_FLAG if is_rpi() else '/tmp/emolt'
    unlink(p) if exists(p) else pathlib.Path(p).touch()


def cb_toggle_aws_s3_group():
    p = LI_PATH_GROUPED_S3_FILE_FLAG if is_rpi() else '/tmp/aws_s3_group'
    unlink(p) if exists(p) else pathlib.Path(p).touch()


def cb_toggle_gps_external():
    p = LI_PATH_DDH_GPS_EXTERNAL if is_rpi() else '/tmp/gps_external'
    unlink(p) if exists(p) else pathlib.Path(p).touch()


def cb_toggle_gps_dummy():
    p = TMP_PATH_GPS_DUMMY if is_rpi() else '/tmp/gps_dummy'
    unlink(p) if exists(p) else pathlib.Path(p).touch()


def cb_toggle_graph_test_mode():
    p = TMP_PATH_GRAPH_TEST_MODE_JSON if is_rpi() else '/tmp/graph_test_mode'
    unlink(p) if exists(p) else pathlib.Path(p).touch()


def _toggle_crontab(s):
    cf = '/etc/crontab'
    cf_run = f'/home/pi/li/ddt/_dt_files/crontab_{s}.sh'
    if sh(f'grep -q crontab_{s}.sh {cf}') == 1:
        # string NOT FOUND in file /etc/crontab, add it
        sh('echo -e "* * * * * pi {cf_run}\n" | sudo tee -a $CF')
        _p(f"added {s} to {cf}")
        return

    # string is there, detect a "commented" symbol
    rv = sh(f"grep crontab_{s}.sh {cf} | grep -F '#' > /dev/null")

    # delete any lines containing "crontab_ddh.sh"
    sh(f"sudo sed -i '/crontab_{s}/d' {cf}")

    if rv == 0:
        _p(f"crontab {s} was OFF, enabling it")
        sh(f'echo "* * * * * pi {cf_run}" | sudo tee -a {cf}')
    else:
        _p(f"crontab {s} was ON, disabling it")
        sh(f'echo "#* * * * * pi {cf_run}" | sudo tee -a {cf}')

    # restart the cron service
    sh("sudo systemctl restart cron.service")
    _p("crontab service restarted")


def cb_toggle_crontab_ddh():
    return _toggle_crontab('ddh')


def cb_toggle_crontab_api():
    return _toggle_crontab('api')


def cb_run_script_gps_test():
    from scripts.script_test_gps_quectel import main_test_gps_quectel
    if is_rpi():
        main_test_gps_quectel()
    else:
        _p('no-RPI: no test GPS quectel')


def cb_run_script_buttons_test():
    from scripts.script_test_box_buttons import main_test_box_buttons
    if is_rpi():
        main_test_box_buttons()
    else:
        _p('no-RPI: no test box buttons')


def cb_provision_ddh():
    provision_ddh()


def cb_quit():
    _p('quitting DDC')
    sys.exit(0)


op = {
    f"{g_fem} toggle emolt marker": cb_toggle_emolt_marker,
    f"{g_fag} toggle AWS s3 group": cb_toggle_aws_s3_group,
    f"{g_fge} toggle GPS external": cb_toggle_gps_external,
    f"{g_fgd} toggle GPS dummy": cb_toggle_gps_dummy,
    f"{g_fem} toggle graph test mode": cb_toggle_graph_test_mode,
    f"{g_fcd} toggle crontab DDH": cb_toggle_crontab_ddh,
    f"{g_fca} toggle crontab API": cb_toggle_crontab_api,
    "provision DDH": cb_provision_ddh,
    "test GPS Quectel": cb_run_script_gps_test,
    "test buttons": cb_run_script_buttons_test,
    "kill ddh": cb_kill_ddh,
    "kill lxpanel": cb_kill_lxpanel,
    "quit": cb_quit,
}


def main_ddc():
    while 1:
        system('clear')

        # obtain current flags
        cb_get_current_flags()

        # selection
        menu = Bullet(
            prompt="\nChoose operation to perform:",
            choices=list(op.keys()),
            indent=0,
            align=5,
            margin=2,
            shift=0,
            bullet="-->",
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
