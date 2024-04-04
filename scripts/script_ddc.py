#!/usr/bin/env python3


import multiprocessing
import os
import pathlib
import subprocess as sp
import sys
import time
from os.path import exists
from os import unlink
from bullet import Bullet
from scripts.script_provision_get import get_provision_ddh
from utils.ddh_config import cfg_load_from_file, cfg_save_to_file
from utils.tmp_paths import (
    LI_PATH_GROUPED_S3_FILE_FLAG,
    LI_PATH_DDH_GPS_EXTERNAL,
    TMP_PATH_GPS_DUMMY, TMP_PATH_GRAPH_TEST_MODE_JSON,
    DDH_USES_SHIELD_JUICE4HALT, DDH_USES_SHIELD_SAILOR)


VP_RBL = '0403:6001'
VP_QUECTEL = '2c7c:0125'
VP_GPS_PUCK_1 = '067B:2303'
VP_GPS_PUCK_2 = '067B:23A3'
FLAG_CLONED_BALENA = '/home/pi/.ddh_cloned_w_balena'
MD5_MOD_BTUART = '95da1d6d0bea327aa5426b7f90303778'


def _p(s):
    print(s)


def _tdr(t=3):
    # some time so user can read results displayed
    time.sleep(t)


def _per(s):
    # red
    print("{}{}{}".format('\033[91m', s, '\033[0m'))


def _pok(s):
    # green
    print("{}{}{}".format('\033[92m', s, '\033[0m'))


def _pwr(s):
    # yellow
    print("{}{}{}".format('\033[93m', s, '\033[0m'))


def sh(c):
    rv = sp.run(c, shell=True, stdout=sp.PIPE, stderr=sp.PIPE)
    return rv.returncode


def sho(c):
    rv = sp.run(c, shell=True, stdout=sp.PIPE, stderr=sp.PIPE)
    return rv.returncode, rv.stdout


def is_rpi():
    return sh('cat /proc/cpuinfo | grep aspberry') == 0


def cb_get_crontab(s):
    assert s in ('api', 'ddh', 'lxp')
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


def refresh_menu_options():
    return {
        # aws group
        "fag": 'yes' if exists(LI_PATH_GROUPED_S3_FILE_FLAG) else 'not',
        # gps external
        "fge": 'yes' if exists(LI_PATH_DDH_GPS_EXTERNAL) else 'not',
        # gps dummy
        "fgd": 'yes' if exists(TMP_PATH_GPS_DUMMY) else 'not',
        # application gear type
        "agt": 'yes' if g_cfg['behavior']['gear_type'] else 'not',
        # graph test
        "fgt": 'yes' if exists(TMP_PATH_GRAPH_TEST_MODE_JSON) else 'not',
        # crontab ddh
        "fcd": 'yes' if cb_get_crontab('ddh') else 'not',
        # crontab api
        "fca": 'yes' if cb_get_crontab('api') else 'not',
        # crontab lxp
        "flx": 'yes' if cb_get_crontab('lxp') else 'not',
        # cloned with balena
        "bal": 'yes' if exists(FLAG_CLONED_BALENA) else 'not',
        # uses shield for power juice_4_halt
        "j4h": 'yes' if exists(DDH_USES_SHIELD_JUICE4HALT) else 'not',
        # uses shield for power sailor
        "sai": 'yes' if exists(DDH_USES_SHIELD_SAILOR) else 'not',
    }


# run check
g_cfg = cfg_load_from_file()


def cb_toggle_gear_type():
    global g_cfg
    gt = g_cfg['behavior']['gear_type']
    gt ^= 1
    cfg_save_to_file(g_cfg)
    g_cfg = cfg_load_from_file()


def cb_kill_ddh():
    for c in (
            'killall main_ddh',
            'killall main_dds',
            'killall main_ddh_controller',
            'killall main_dds_controller'
    ):
        sh(c)
    _p('sent kill signal to DDH software')

    # also kill any desktop terminal containing it
    # pi 29327 ..... 0:00 x-terminal-emulator -e /home/pi/Desktop/DDH.sh
    rv, s = sho(f'ps -aux | grep x-terminal-emulator | grep DDH')
    if rv == 0:
        _p('sent kill signal to x-terminal containing DDH')
        s = s.decode().split()
        pid = s[1]
        sh(f'kill -9 {pid}')

    _tdr()


def cb_calibrate_display():
    ok_arch_aarch64 = sh('arch | grep aarch64') == 0
    if ok_arch_aarch64:
        c = "export XAUTHORITY=/home/pi/.Xauthority; " \
            "export DISPLAY=:0; " \
            "xinput_calibrator"
        sh(c)
    else:
        print('only need to calibrate 64-bits systems')
        return

    # file has to be copied to
    # /etc/X11/xorg.conf.d/99-calibration.conf
    _tdr(10)


def cb_message_box():
    # src: ostechnix zenity-create-gui-dialog-boxes-in-bash-scripts/
    c = "export XAUTHORITY=/home/pi/.Xauthority; "\
        "export DISPLAY=:0; "\
        "zenity --info --title \"DDC test\" --text \"DDH says hi\" "\
        "--timeout 3"
    _p('check for pop up in DDH screen')
    sh(c)
    _tdr()


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


def _cb_toggle_crontab(s):
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
    return _cb_toggle_crontab('ddh')


def cb_toggle_crontab_api():
    return _cb_toggle_crontab('api')


def cb_toggle_crontab_lxp():
    return _cb_toggle_crontab('lxp')


def cb_run_script_gps_test():
    try:
        from scripts.script_test_gps_quectel import main_test_gps_quectel
        if is_rpi():
            if sh(f'lsusb | grep {VP_QUECTEL}') == 0:
                main_test_gps_quectel()
            else:
                _per('no GPS quectel hardware detected')
                _tdr()
        else:
            _p('no-RPI: no test GPS quectel')
            _tdr()
    except (Exception, ) as ex:
        _per(f'exception cb_run_script_gps_test -> {ex}')
        _tdr()


def cb_run_script_buttons_test():
    try:
        from scripts.script_test_box_buttons import main_test_box_buttons
        if is_rpi():
            main_test_box_buttons()
        else:
            _per('no-RPI: no test box buttons')
            _tdr()
    except (Exception, ) as ex:
        _per(f'exception cb_run_script_buttons_test -> {ex}')
        _tdr()


def cb_run_script_dox_test():
    try:
        from scripts.script_logger_do_deploy import main_logger_do_deploy
        main_logger_do_deploy()
        _tdr()
    except (Exception, ) as ex:
        _per(f'exception cb_run_script_dox_test -> {ex}')
        _tdr()


def cb_provision_ddh():
    get_provision_ddh()


def cb_quit():
    _p('quitting DDC')
    sys.exit(0)


def cb_toggle_flag_balena():
    p = FLAG_CLONED_BALENA if is_rpi() else '/tmp/flag_balena'
    unlink(p) if exists(p) else pathlib.Path(p).touch()


def cb_see_flag_j4h():
    return sh(f'ls {DDH_USES_SHIELD_JUICE4HALT}') == 0


def cb_see_flag_sailor():
    # todo ---> soon
    return 0


# contains errors in system check
str_e = ''
str_w = ''


def _run_check():

    global str_e
    str_e = ''
    global str_w
    str_w = ''

    def _e(s):
        global str_e
        str_e += f'     - {s}\n'

    def _w(s):
        global str_w
        str_w += f'     - {s}\n'

    def _check_fw_cell():
        c = "echo -ne 'AT+CVERSION\r' > /dev/ttyUSB2"
        sh(c)
        c = "cat -v < /dev/ttyUSB2 | grep 2022"
        return sh(c) == 0

    def _check_aws_credentials():
        f = g_cfg['credentials']
        for k, v in f.items():
            if not v:
                if 'custom' not in k:
                    _e(f'config.toml no credential {k}')
                    return 0
                else:
                    _w(f'config.toml no custom credential {k}')
                    return 1
        return 1

    # -----------------------------------------------------
    # issue: Raspberry Pi reference 2023-05-03
    # arch: armv7l
    # is_rpi3: Raspberry Pi 3 Model B Plus Rev 1.3
    # hostname: raspberrypi
    # hardware flags
    # grep exact (-w) for 'active' detection
    # dwservice
    # -----------------------------------------------------
    ok_issue = sh('cat /boot/issue.txt | grep 2023-05-03') == 0
    ok_arch_armv7l = sh('arch | grep armv7l') == 0
    is_rpi3 = sh("cat /proc/cpuinfo | grep 'aspberry Pi 3'") == 0
    ok_hostname = sh('hostname | grep raspberrypi') == 0
    flag_gps_ext = sh(f'[ -f {LI_PATH_DDH_GPS_EXTERNAL} ]') == 0
    flag_vp_gps_puck1 = sh(f'lsusb | grep {VP_GPS_PUCK_1}') == 0
    flag_vp_gps_puck2 = sh(f'lsusb | grep {VP_GPS_PUCK_2}') == 0
    flag_vp_quectel = sh(f'lsusb | grep {VP_QUECTEL}') == 0
    flag_mod_btuart = sh(f'md5sum /usr/bin/btuart | grep {MD5_MOD_BTUART}') == 0
    flag_rbl_en = int(g_cfg['flags']['rbl_en'])
    ok_ble_v = sh('bluetoothctl -v | grep 5.66') == 0
    _c = 'systemctl is-active unit_switch_net.service | grep -w active'
    ok_service_cell_sw = sh(_c) == 0
    ok_fw_cell = _check_fw_cell()
    ok_internet_via_cell = sh('ping -I ppp0 www.google.com -c 1') == 0
    ok_dwservice = sh('ps -aux | grep dwagent') == 0
    ok_aws_cred = _check_aws_credentials()
    ok_crontab_ddh = cb_get_crontab('ddh') == 1
    ok_crontab_api = cb_get_crontab('api') == 1
    ok_crontab_lxp = cb_get_crontab('lxp') == 1
    ok_shield_j4h = cb_see_flag_j4h() == 1
    ok_shield_sailor = cb_see_flag_sailor() == 1

    # -----------------
    # check conflicts
    # -----------------
    rv = 0
    if not ok_aws_cred:
        # error indicated inside other function
        rv += 1
    if not ok_shield_j4h and not ok_shield_sailor:
        _w('none of the 2 supported power shields detected')
    if not ok_internet_via_cell:
        _e('no cell internet')
        rv += 1
    if not ok_dwservice:
        _e('dws not running')
        rv += 1
    if not ok_fw_cell:
        _e('bad fw_cell')
        rv += 1
    if not ok_service_cell_sw:
        _e('not running service_cell_sw')
    if not ok_ble_v != '5.66':
        _e('bad bluez version')
        rv += 1
    if not ok_issue:
        _e('bad raspberryos file /boot/issue.txt')
        rv += 1
    if not ok_arch_armv7l:
        _e('bad arch')
        rv += 1
    if not ok_hostname:
        _e('bad hostname')
        rv += 1
    if flag_gps_ext and not flag_vp_gps_puck1 and not flag_vp_gps_puck2:
        _e('GPS external set but not detected')
        rv += 1
    if is_rpi3 and not flag_mod_btuart:
        _e(f'is_rpi3 {is_rpi3}, bad mod_uart')
        rv += 1
    if flag_rbl_en and not VP_RBL:
        _e('rbl_en but not detected')
        rv += 1
    if not ok_crontab_ddh:
        _e('crontab DDH not set')
    if not ok_crontab_api:
        _e('crontab API not set')
    if not ok_crontab_lxp:
        _e('crontab LXP not set')
    if not (flag_vp_quectel or flag_vp_gps_puck1 or flag_vp_gps_puck2):
        _e('no real GPS hardware present')
    return rv, str_e, str_w


def main_ddc():

    while 1:

        # show summary
        rv, e, w = _run_check()
        print('\n DDH automatic check:')
        if rv:
            _per(f'     [ ER ] system NOT ready, see errors next')
            print(str_e)
        else:
            _pok(f'     [ OK ] system ready')
        if w:
            _pwr(f'     [ OK ] warning')
            print(str_w)

        # obtain current flags
        g_chk = refresh_menu_options()
        menu_options = {
            f"[ {g_chk['fag']} ] is AWS s3 group": cb_toggle_aws_s3_group,
            f"[ {g_chk['fge']} ] is GPS hardware puck": cb_toggle_gps_external,
            f"[ {g_chk['fgd']} ] is GPS dummy": cb_toggle_gps_dummy,
            f"[ {g_chk['agt']} ] is app gear trawling": cb_toggle_gear_type,
            f"[ {g_chk['fgt']} ] is graph test mode": cb_toggle_graph_test_mode,
            f"[ {g_chk['fcd']} ] is crontab DDH on": cb_toggle_crontab_ddh,
            f"[ {g_chk['fca']} ] is crontab API on": cb_toggle_crontab_api,
            f"[ {g_chk['flx']} ] is crontab LXP on": cb_toggle_crontab_lxp,
            f"| {g_chk['bal']} | is flag balena": cb_toggle_flag_balena,
            f"| {g_chk['j4h']} | is j4h_shield": cb_see_flag_j4h,
            f"| {g_chk['j4h']} | is j4h_shield": cb_see_flag_sailor,
            "provision (caution)": cb_provision_ddh,
            "test GPS Quectel": cb_run_script_gps_test,
            "test box side buttons": cb_run_script_buttons_test,
            "kill DDH application": cb_kill_ddh,
            "calibrate DDH display": cb_calibrate_display,
            "say hi to desktop": cb_message_box,
            "run script logger oxygen deploy": cb_run_script_dox_test(),
            "quit": cb_quit,
        }

        # selection
        menu = Bullet(
            prompt=" DDH manual checks:",
            choices=list(menu_options.keys()),
            indent=0,
            align=5,
            margin=2,
            shift=0,
            bullet=">>",
            pad_right=5,
            return_index=True
        )

        # _: text, i: index
        txt, i = menu.launch()

        # run the callbacks
        chosen_cb = list(menu_options.values())[i]

        if txt == 'quit':
            break

        # some space to see answer
        print('\n')

        p = multiprocessing.Process(target=chosen_cb)
        p.start()
        p.join()

        # see results
        if is_rpi():
            os.system('clear')
        else:
            print('\n\n\n\n\n')


if __name__ == '__main__':
    # don't run from here but main_ddc.py
    assert 0
