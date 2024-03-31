#!/usr/bin/env python3


import multiprocessing
import pathlib
import subprocess as sp
import sys
import time
from collections import namedtuple
from os.path import exists
from os import unlink
from os import system
from bullet import Bullet

from main_chk import run_hardware_check
from scripts.script_provision_get import provision_ddh
from utils.ddh_config import cfg_load_from_file, cfg_save_to_file
from utils.tmp_paths import (
    LI_PATH_GROUPED_S3_FILE_FLAG,
    LI_PATH_DDH_GPS_EXTERNAL,
    TMP_PATH_GPS_DUMMY, TMP_PATH_GRAPH_TEST_MODE_JSON)

# run hardware check
g_rhc = 0

# run software check
nt_rsc = namedtuple("nt_rsc",
                    # aws group
                    ["fag",
                     # gps external
                     "fge",
                     # gps dummy
                     "fgd",
                     # graph test
                     "fgt",
                     # crontab ddh
                     "fcd",
                     # crontab api
                     "fca",
                     # config file
                     "cfg"])


def _p(s):
    print(s)


def sh(c):
    rv = sp.run(c, shell=True, stdout=sp.PIPE, stderr=sp.PIPE)
    return rv.returncode


def is_rpi():
    return sh('cat /proc/cpuinfo | grep aspberry') == 0


def cb_get_crontab(s):
    assert s in ('api', 'ddh')
    s = f'crontab_{s}.sh'
    # assume crontab off
    cf = '/etc/crontab'
    if sh(f'grep -q {s} {cf}') == 0:
        # line crontab ddh present, check if commented or not
        return sh(f"grep {s} {cf} | grep -F '#' > /dev/null")
        # todo ---> test this


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
    c = "export XAUTHORITY=/home/pi/.Xauthority; " \
        "export DISPLAY=:0; " \
        "sudo lxpanelctl restart"
    sh(c)
    _p('sent kill signal to lxpanel')
    time.sleep(2)


def cb_message_box():
    # src: ostechnix zenity-create-gui-dialog-boxes-in-bash-scripts/
    c = "export XAUTHORITY=/home/pi/.Xauthority; "\
        "export DISPLAY=:0; "\
        "zenity --info --title \"DDC test\" --text \"DDH says hi\" "\
        "--timeout 3"
    _p('check for pop up in DDH screen')
    sh(c)
    time.sleep(3)


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


def cb_check_run():
    # HARDWARE test
    run_hardware_check()


def cb_quit():
    _p('quitting DDC')
    sys.exit(0)


# start empty
g_rsc = nt_rsc(
    fag=None,
    fge=None,
    fgd=None,
    fgt=None,
    fcd=None,
    fca=None,
    cfg=None
)


def cb_get_current_flags():
    global g_rsc
    g_rsc = nt_rsc(
        fag=int(exists(LI_PATH_GROUPED_S3_FILE_FLAG)),
        fge=int(exists(LI_PATH_DDH_GPS_EXTERNAL)),
        fgd=int(exists(TMP_PATH_GPS_DUMMY)),
        fgt=int(exists(TMP_PATH_GRAPH_TEST_MODE_JSON)),
        fcd=int(cb_get_crontab('ddh')),
        fca=int(cb_get_crontab('api')),
        cfg=cfg_load_from_file()
    )


def cb_set_boat_info():
    a = input('enter boat name ->')
    global g_rsc
    g_rsc.cfg['behavior']['ship_name'] = a
    while a not in ('0', '1'):
        a = input('enter application gear type ->')
    g_rsc.cfg['behavior']['gear_type'] = a
    cfg_save_to_file(g_rsc.cfg)


def cb_run_hardware_check():
    global g_rhc
    g_rhc = run_hardware_check()


menu_options = {
    f"{g_rhc} run hardware check": cb_run_hardware_check,
    f"{g_rsc.fag} toggle AWS s3 group": cb_toggle_aws_s3_group,
    f"{g_rsc.fge} toggle GPS external": cb_toggle_gps_external,
    f"{g_rsc.fgd} toggle GPS dummy": cb_toggle_gps_dummy,
    f"{g_rsc.fgt} toggle graph test mode": cb_toggle_graph_test_mode,
    f"{g_rsc.fcd} toggle crontab DDH": cb_toggle_crontab_ddh,
    f"{g_rsc.fca} toggle crontab API": cb_toggle_crontab_api,
    "DDH set boat info": cb_set_boat_info,
    "DDH check run": cb_check_run,
    "DDH kill application": cb_kill_ddh,
    "DDH provision": cb_provision_ddh,
    "DDH message hello": cb_message_box,
    "DDH test GPS Quectel": cb_run_script_gps_test,
    "DDH test buttons": cb_run_script_buttons_test,
    "DDH kill lxpanel": cb_kill_lxpanel,
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
            choices=list(menu_options.keys()),
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
        chosen_cb = list(menu_options.values())[i]

        if txt == 'quit':
            break

        p = multiprocessing.Process(target=chosen_cb)
        p.start()
        p.join()


if __name__ == '__main__':
    # don't run from here but main_ddc.py
    assert 0
