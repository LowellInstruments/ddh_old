#!/usr/bin/env python3


import sys
import time
from os import unlink
import py_cui
from py_cui.keys import *
from os.path import exists

from scripts.script_provision_get import get_provision_ddh, ping_provision_server
# from scripts.script_provision_get import get_provision_ddh
from utils.ddh_config import cfg_load_from_file, cfg_save_to_file
from utils.tmp_paths import (
    LI_PATH_GROUPED_S3_FILE_FLAG,
    LI_PATH_DDH_GPS_EXTERNAL,
    TMP_PATH_GPS_DUMMY, TMP_PATH_GRAPH_TEST_MODE_JSON,
    DDH_USES_SHIELD_JUICE4HALT,
    DDH_USES_SHIELD_SAILOR, LI_PATH_SKIP_IN_PORT_FILE_FLAG
)
import pathlib
import subprocess as sp


VP_RBL = '0403:6001'
VP_QUECTEL = '2c7c:0125'
VP_GPS_PUCK_1 = '067B:2303'
VP_GPS_PUCK_2 = '067B:23A3'
MD5_MOD_BTUART = '95da1d6d0bea327aa5426b7f90303778'
TMP_DDC_ERR = '/tmp/ddc_err'


# cwd is ddh here
path_script_deploy_dox = 'scripts/run_script_deploy_logger_dox.sh'
path_script_deploy_tdo = 'scripts/run_script_deploy_logger_tdo.sh'


def sh(c):
    rv = sp.run(c, shell=True, stdout=sp.PIPE, stderr=sp.PIPE)
    return rv.returncode


def sho(c):
    rv = sp.run(c, shell=True, stdout=sp.PIPE, stderr=sp.PIPE)
    return rv.returncode, rv.stdout.decode()


def is_rpi():
    return sh('cat /proc/cpuinfo | grep aspberry') == 0


def cb_do_nothing():
    pass


def cb_aws_s3_group():
    p = LI_PATH_GROUPED_S3_FILE_FLAG
    unlink(p) if exists(p) else pathlib.Path(p).touch()


def cb_gps_external():
    p = LI_PATH_DDH_GPS_EXTERNAL
    unlink(p) if exists(p) else pathlib.Path(p).touch()


def cb_gps_dummy():
    p = TMP_PATH_GPS_DUMMY
    unlink(p) if exists(p) else pathlib.Path(p).touch()


def cb_graph_test_mode():
    p = TMP_PATH_GRAPH_TEST_MODE_JSON
    unlink(p) if exists(p) else pathlib.Path(p).touch()


def cb_skip_dl_in_port():
    p = LI_PATH_SKIP_IN_PORT_FILE_FLAG
    unlink(p) if exists(p) else pathlib.Path(p).touch()


def cb_get_flag_j4h():
    return sh(f'ls {DDH_USES_SHIELD_JUICE4HALT}') == 0


def cb_get_flag_sailor():
    return sh(f'ls {DDH_USES_SHIELD_SAILOR}') == 0


def cb_provision_ddh():
    if not ping_provision_server():
        return
    # get_provision_ddh()


def cb_quit():
    sys.exit(0)


def get_crontab(s):
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


def get_gear_type():
    c = cfg_load_from_file()
    return c['behavior']['gear_type']


def cb_gear_type():
    c = cfg_load_from_file()
    c['behavior']['gear_type'] ^= 1
    cfg_save_to_file(c)


def cb_kill_ddh():
    for c in (
            'killall main_ddh',
            'killall main_dds',
            'killall main_ddh_controller',
            'killall main_dds_controller'
    ):
        sh(c)

    # also kill any desktop terminal containing it
    # pi 29327 ..... 0:00 x-terminal-emulator -e /home/pi/Desktop/DDH.sh
    rv, s = sho(f'ps -aux | grep x-terminal-emulator | grep DDH')
    if rv == 0:
        s = s.split()
        pid = s[1]
        sh(f'kill -9 {pid}')


def _es(e):
    # error set
    if not e:
        return
    with open(TMP_DDC_ERR, 'a') as f:
        f.write(f'error: {e}\n')


def cb_test_gps_quectel():
    try:
        from scripts.script_test_gps_quectel import main_test_gps_quectel
        if is_rpi():
            if sh(f'lsusb | grep {VP_QUECTEL}') == 0:
                main_test_gps_quectel()
            else:
                _es('no puck')
        else:
            _es('no Rpi for GPS quectel test')
    except (Exception, ) as ex:
        _es(str(ex))


def cb_test_buttons():
    try:
        from scripts.script_test_box_buttons import main_test_box_buttons
        if is_rpi():
            main_test_box_buttons()
        else:
            _es('no Rpi for buttons test')
    except (Exception, ) as ex:
        _es(str(ex))


def cb_run_deploy_dox():
    try:
        # do this or this script's prompts fail
        sp.run(path_script_deploy_dox)
    except (Exception, ) as ex:
        _es(f'{ex} running deploy_dox')


def cb_run_deploy_tdo():
    try:
        # do this or this script's prompts fail
        sp.run(path_script_deploy_tdo)
    except (Exception, ) as ex:
        _es(f'{ex} running deploy_tdo')


def cb_calibrate_display():
    ok_arch_aarch64 = sh('arch | grep aarch64') == 0
    if not ok_arch_aarch64:
        _es('only calibrate on aarch64')
        return

    c = "export XAUTHORITY=/home/pi/.Xauthority; " \
        "export DISPLAY=:0; " \
        "xinput_calibrator"
    sh(c)
    # file has to be copied to
    # /etc/X11/xorg.conf.d/99-calibration.conf
    # todo ---> do this moving of xorg file


def _cb_crontab(s):
    cf = '/etc/crontab'
    cf_run = f'/home/pi/li/ddt/_dt_files/crontab_{s}.sh'
    if sh(f'grep -q crontab_{s}.sh {cf}') == 1:
        # string NOT FOUND in file /etc/crontab, add it
        sh(f'echo "* * * * * pi {cf_run}" | sudo tee -a {cf}')
        # new line because -e sucks
        sh(f'echo "" | sudo tee -a {cf}')
        return

    # string is there, detect a "commented" symbol
    rv = sh(f"grep crontab_{s}.sh {cf} | grep -F '#' > /dev/null")

    # delete any lines containing "crontab_ddh.sh"
    sh(f"sudo sed -i '/crontab_{s}/d' {cf}")

    if rv == 0:
        sh(f'echo "* * * * * pi {cf_run}" | sudo tee -a {cf}')
    else:
        sh(f'echo "#* * * * * pi {cf_run}" | sudo tee -a {cf}')

    # restart the cron service
    sh("sudo systemctl restart cron.service")


# needed because we cannot call with parameters from menu
def cb_crontab_ddh(): return _cb_crontab('ddh')
def cb_crontab_api(): return _cb_crontab('api')
def cb_crontab_lxp(): return _cb_crontab('lxp')


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
        str_e += f'   - {s}\n'

    def _w(s):
        global str_w
        str_w += f'   - {s}\n'

    def _check_fw_cell():
        c = "echo -ne 'AT+CVERSION\r' > /dev/ttyUSB2"
        sh(c)
        c = "cat -v < /dev/ttyUSB2 | grep 2022"
        return sh(c) == 0

    def _check_aws_credentials():
        c = cfg_load_from_file()
        f = c['credentials']
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
    ok_issue_20240315 = sh('cat /boot/issue.txt | grep 2024-03-15') == 0
    ok_issue_20230503 = sh('cat /boot/issue.txt | grep 2023-05-03') == 0
    ok_issue_20220922 = sh('cat /boot/issue.txt | grep 2022-09-22') == 0
    ok_arch_armv7l = sh('arch | grep armv7l') == 0
    ok_arch_aarch64 = sh('arch | grep aarch64') == 0
    is_rpi3 = sh("cat /proc/cpuinfo | grep 'aspberry Pi 3'") == 0
    ok_hostname = sh('hostname | grep raspberrypi') == 0
    flag_gps_ext = sh(f'[ -f {LI_PATH_DDH_GPS_EXTERNAL} ]') == 0
    flag_vp_gps_puck1 = sh(f'lsusb | grep {VP_GPS_PUCK_1}') == 0
    flag_vp_gps_puck2 = sh(f'lsusb | grep {VP_GPS_PUCK_2}') == 0
    flag_vp_quectel = sh(f'lsusb | grep {VP_QUECTEL}') == 0
    flag_mod_btuart = sh(f'md5sum /usr/bin/btuart | grep {MD5_MOD_BTUART}') == 0
    cfg = cfg_load_from_file()
    flag_rbl_en = int(cfg['flags']['rbl_en'])
    ok_ble_v = sh('bluetoothctl -v | grep 5.66') == 0
    _c = 'systemctl is-active unit_switch_net.service | grep -w active'
    ok_service_cell_sw = sh(_c) == 0
    ok_fw_cell = _check_fw_cell()
    ok_internet_via_cell = sh('ping -I ppp0 www.google.com -c 1') == 0
    ok_dwservice = sh('ps -aux | grep dwagent') == 0
    ok_aws_cred = _check_aws_credentials()
    ok_crontab_ddh = get_crontab('ddh') == 1
    ok_crontab_api = get_crontab('api') == 1
    ok_crontab_lxp = get_crontab('lxp') == 1
    ok_shield_j4h = cb_get_flag_j4h() == 1
    ok_shield_sailor = cb_get_flag_sailor() == 1

    # check conflicts
    rv = 0
    if not ok_aws_cred:
        # error indicated inside other function
        rv += 1
    if not ok_shield_j4h and not ok_shield_sailor:
        _w('none of 2 supported power shields detected')
    if not ok_internet_via_cell:
        _e('no cell internet')
        rv += 1
    if not ok_dwservice:
        _e('dws not running')
        rv += 1
    if not ok_fw_cell:
        _w('bad fw_cell')
    if not ok_service_cell_sw:
        _e('not running service_cell_sw')
    if not ok_ble_v != '5.66':
        _e('bad bluez version')
        rv += 1
    if not (ok_arch_armv7l and ok_issue_20230503 and ok_issue_20220922) and \
            not (ok_arch_aarch64 and ok_issue_20240315):
        _e('bad arch / file /boot/issue.txt combination')
        rv += 1
    if not ok_hostname:
        _e('bad hostname')
        rv += 1
    if flag_gps_ext and not flag_vp_gps_puck1 and not flag_vp_gps_puck2:
        _e('GPS external puck: set but not detected')
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
        _e('no hardware GPS present')
    if not ok_shield_sailor and not ok_shield_j4h:
        _e('no hardware power shield present')
    return rv, str_e, str_w


class DDC:

    def refresh(self):
        # data
        self.d = {
            'set AWS S3 group': (cb_aws_s3_group, 1 if exists(LI_PATH_GROUPED_S3_FILE_FLAG) else 0),
            'set GPS external puck': (cb_gps_external, 1 if exists(LI_PATH_DDH_GPS_EXTERNAL) else 0),
            'set gear type': (cb_gear_type, get_gear_type()),
            'set GPS dummy': (cb_gps_dummy, 1 if exists(TMP_PATH_GPS_DUMMY) else 0),
            'set graph test mode': (cb_graph_test_mode, 1 if exists(TMP_PATH_GRAPH_TEST_MODE_JSON) else 0),
            'set skip_dl_in_port': (cb_skip_dl_in_port, 1 if exists(LI_PATH_SKIP_IN_PORT_FILE_FLAG) else 0),
            # 'is shield juice4halt': (cb_do_nothing, 1 if exists(DDH_USES_SHIELD_JUICE4HALT) else 0),
            # 'is shield sailor_hat': (cb_do_nothing, 1 if exists(DDH_USES_SHIELD_SAILOR) else 0),
            'set crontab DDH': (cb_crontab_ddh, get_crontab('ddh')),
            #'set crontab API': (cb_crontab_api, get_crontab('api')),
            #'set crontab LXP': (ccb_crontab_lxp, get_crontab('lxp')),
            'provision keys': (cb_provision_ddh, ''),
            'kill DDH application': (cb_kill_ddh, 0),
            'calibrate DDH display': (cb_calibrate_display, 0),
            'test GPS Quectel': (cb_test_gps_quectel, 0),
            'test box side buttons': (cb_test_buttons, 0),
            'deploy logger DOX': (cb_run_deploy_dox, 0),
            'deploy logger TDO': (cb_run_deploy_tdo, 0),
            'quit': (cb_quit, 0)
        }

        # column 1, menu of commands
        self.m = self.r.add_scroll_menu(
            title='Choose command',
            row=1, column=0, row_span=5, padx=5
        )

        # column 2, results and error
        self.s = self.r.add_block_label(
            title='Summary',
            row=1, column=1, row_span=5, center=False, padx=5
        )

        # fill menu of commands
        for k, v in self.d.items():
            if 'set' in k:
                self.m.add_item(f'{v[1]} / {k}')
            else:
                self.m.add_item(f'{k}')

        self.m.add_key_command(KEY_ENTER, command=self.menu_key_enter_cb)

        # fill output label
        rv, e, w = _run_check()
        if rv:
            self.s.set_color(py_cui.RED_ON_BLACK)
            self.s.set_title('DDH config errors found:\n' + e)
        else:
            if w:
                self.s.set_title(w)
            else:
                self.s.set_title('OK')

        # focus
        self.r.move_focus(self.m)

    def __init__(self, root_window: py_cui.PyCUI):
        self.r = root_window
        self.d = None
        self.m = None
        self.s = None
        self.refresh()

    def menu_key_enter_cb(self):
        ch = self.m.get()
        # c: 1 / fag
        if '/' in ch:
            ch = ch.split(' / ')[1]
        for i, k in enumerate(self.d.keys()):
            if ch in k:
                # call the callback
                cb, v = self.d[k]
                cb()
                # go back to main loop
                self.r.stop()
