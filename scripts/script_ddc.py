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

from mat.ble.ble_mat_utils import ble_mat_get_bluez_version
from scripts.script_provision_get import provision_ddh
from utils.ddh_config import cfg_load_from_file, cfg_save_to_file
from utils.tmp_paths import (
    LI_PATH_GROUPED_S3_FILE_FLAG,
    LI_PATH_DDH_GPS_EXTERNAL,
    TMP_PATH_GPS_DUMMY, TMP_PATH_GRAPH_TEST_MODE_JSON)


vp_rb = '0403:6001'
vp_quectel = '2c7c:0125'
vp_gps_puck_1 = '067B:2303'
vp_gps_puck_2 = '067B:23A3'
vp_ssd = '045b:0229'
FLAG_CLONED_BALENA = '/home/pi/.ddh_cloned_w_balena'
MD5_MOD_BTUART = '95da1d6d0bea327aa5426b7f90303778'


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
    if sh(f'grep -q {s} {cf}'):
        # line NOT even present
        return 0
    # line IS present, search for special character with 'F'
    if sh(f"grep {s} {cf} | grep -F '#' > /dev/null") == 0:
        return 0
    # line IS present and uncommented
    return 1


# run check
g_c = {
    # aws group
    "fag": int(exists(LI_PATH_GROUPED_S3_FILE_FLAG)),
    # gps external
    "fge": int(exists(LI_PATH_DDH_GPS_EXTERNAL)),
    # gps dummy
    "fgd": int(exists(TMP_PATH_GPS_DUMMY)),
    # graph test
    "fgt": int(exists(TMP_PATH_GRAPH_TEST_MODE_JSON)),
    # crontab ddh
    "fcd": int(cb_get_crontab('ddh')),
    # crontab api
    "fca": int(cb_get_crontab('api')),
    # config file
    "cfg": cfg_load_from_file()
}


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


def cb_quit():
    _p('quitting DDC')
    sys.exit(0)


def cb_set_boat_name():
    a = input('enter boat name ->')
    g_c['cfg']['behavior']['ship_name'] = a
    cfg_save_to_file(g_c['cfg'])


def cb_set_boat_gear_type():
    a = None
    while a not in ('0', '1'):
        a = input('enter application gear type ->')
    g_c['cfg']['behavior']['gear_type'] = a
    cfg_save_to_file(g_c['cfg'])


def _run_check():

    def _e(s):
        print(f'    - error -> {s}')

    def _w(s):
        print(f'    - alert -> {s}')

    def _fw_cell():
        c = "echo -ne 'AT+CVERSION\r' > /dev/ttyUSB2"
        sh(c)
        c = "cat -v < /dev/ttyUSB2 | grep 2022"
        return sh(c) == 0

    def _aws_credentials():
        f = g_c['cfg']['credentials']
        for k, v in f.items():
            if not v:
                _e(f'config.toml no credential {k}')
                return 0
        return 1

    # issue: Raspberry Pi reference 2023-05-03
    ok_issue = sh('cat /boot/issue.txt | grep 2023-05-03') == 0
    # arch: armv7l
    ok_arch_armv7l = sh('arch | grep armv7l') == 0
    # is_rpi3:  Model		: Raspberry Pi 3 Model B Plus Rev 1.3
    is_rpi3 = sh("cat /proc/cpuinfo | grep 'aspberry Pi 3'") == 0
    is_rpi4 = sh("cat /proc/cpuinfo | grep 'aspberry Pi 4'") == 0
    # hostname: raspberrypi
    ok_hostname = sh('hostname | grep raspberrypi') == 0
    # hardware flags
    flag_clone_balena = sh(f'[ -f {FLAG_CLONED_BALENA} ]') == 0
    flag_gps_ext = sh(f'[ -f {LI_PATH_DDH_GPS_EXTERNAL} ]') == 0
    flag_vp_gps_puck1 = sh(f'lsusb | grep {vp_gps_puck_1}') == 0
    flag_vp_gps_puck2 = sh(f'lsusb | grep {vp_gps_puck_2}') == 0
    flag_mod_btuart = sh(f'md5sum /usr/bin/btuart | grep {MD5_MOD_BTUART}') == 0
    flag_rbl_en = int(g_c['cfg']['flags']['rbl_en'])
    ble_v = ble_mat_get_bluez_version()
    # todo ---> improve this one
    service_cell_sw = sh('systemctl is-active unit_switch_net.service')
    ok_fw_cell = _fw_cell()
    ok_internet_via_cell = sh('ping -I ppp0 www.google.com -c 1') == 0
    # dwservice
    ok_dwservice = sh('ps -aux | grep dwagent') == 0
    ok_aws_cred = _aws_credentials()

    # -----------------
    # check conflicts
    # -----------------
    rv = 0
    if not ok_aws_cred:
        # error indicated inside other function
        rv += 1
    if not ok_internet_via_cell:
        _e('bad, no cell internet')
        rv += 1
    if not ok_dwservice:
        _e(f'bad dws, not running')
        rv += 1
    if not ok_fw_cell:
        _e(f'bad fw_cell')
        rv += 1
    # if service_cell_sw != 'active':
    #     _e(f'bad service_cell_sw')
    if ble_v != '5.66':
        _e(f'bad bluez version = {ble_v}')
        rv += 1
    if not ok_issue:
        _e(f'bad raspberryos file /boot/issue.txt')
        rv += 1
    if not ok_arch_armv7l:
        _e(f'bad arch')
        rv += 1
    if not ok_hostname:
        _e(f'bad hostname')
        rv += 1
    if flag_gps_ext and not flag_vp_gps_puck1 and not flag_vp_gps_puck2:
        _e(f'rv_gps_external but not detected')
        rv += 1
    if is_rpi3 and not flag_mod_btuart:
        _e(f'is_rpi3 {is_rpi3} mod_uart')
        rv += 1
    if flag_rbl_en and not vp_rb:
        _e(f'rbl_en but not detected')
        rv += 1
    if not flag_clone_balena:
        _w('box NOT cloned with balena')

    # summary
    return 'BAD'


def main_ddc():
    while 1:
        system('clear')

        # show summary
        g_c['sum'] = _run_check()
        print(f"[ {g_c['sum']} ] DDH system check:")

        # obtain current flags
        menu_options = {
            f"[ {g_c['fag']} ] toggle AWS s3 group": cb_toggle_aws_s3_group,
            f"[ {g_c['fge']} ] toggle GPS external": cb_toggle_gps_external,
            f"[ {g_c['fgd']} ] toggle GPS dummy": cb_toggle_gps_dummy,
            f"[ {g_c['fgt']} ] toggle graph test mode": cb_toggle_graph_test_mode,
            f"[ {g_c['fcd']} ] toggle crontab DDH": cb_toggle_crontab_ddh,
            f"[ {g_c['fca']} ] toggle crontab API": cb_toggle_crontab_api,
            "DDH set boat info": cb_set_boat_name,
            "DDH set boat gear": cb_set_boat_gear_type,
            "DDH provision": cb_provision_ddh,
            "DDH test GPS Quectel": cb_run_script_gps_test,
            "DDH test buttons": cb_run_script_buttons_test,
            "DDH kill application": cb_kill_ddh,
            "DDH kill lxpanel": cb_kill_lxpanel,
            "DDH message hello": cb_message_box,
            "quit": cb_quit,
        }

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
