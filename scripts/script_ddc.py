#!/usr/bin/env python3
import os

import serial
import sys
import time
from os import unlink
from os.path import exists

from mat.quectel import VP_QUECTEL
from scripts.script_provision_get import get_provision_ddh, ping_provision_server
from utils.ddh_config import cfg_load_from_file, cfg_save_to_file
from utils.ddh_shared import get_ddh_folder_path_settings
from utils.find_usb_port_auto import find_n_list_all_usb_port_automatically
from utils.flag_paths import (
    LI_PATH_GROUPED_S3_FILE_FLAG,
    LI_PATH_DDH_GPS_EXTERNAL,
    TMP_PATH_GPS_DUMMY, TMP_PATH_GRAPH_TEST_MODE_JSON,
    DDH_USES_SHIELD_JUICE4HALT,
    DDH_USES_SHIELD_SAILOR, LI_PATH_TEST_MODE
)
import pathlib
import subprocess as sp
from mat.utils import PrintColors as PC



VP_GPS_PUCK_1 = '067B:2303'
VP_GPS_PUCK_2 = '067B:23A3'
MD5_MOD_BTUART = '95da1d6d0bea327aa5426b7f90303778'
TMP_DDC_ERR = '/tmp/ddc_err'
DEBUG_TIME = False


def check_aws_run(f):
    # f: {'cred_aws_bucket': '',
    #     'cred_aws_key_id': '',
    #     'cred_aws_secret': '',
    #     'cred_aws_sqs_queue_name': '',
    _k = f['cred_aws_key_id']
    _s = f["cred_aws_secret"]
    _n = f["cred_aws_bucket"]

    # 0 is bad
    if _k is None or _s is None or _n is None:
        return 0

    # build the AWS command
    c = (
        f'AWS_ACCESS_KEY_ID={_k} AWS_SECRET_ACCESS_KEY={_s} '
        f'aws s3 ls s3://{_n}'
    )

    # run test AWS ls command
    try:
        rv = sp.run(c, shell=True, stdout=sp.PIPE, stderr=sp.PIPE, timeout=10)
        if rv.returncode:
            print(f'error: listing buckets {rv.stderr}')
            return 0
    except (Exception, ) as ex:
        print(f'error: check_aws_run -> {ex}')
        return 0
    return 1


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


def cb_test_mode():
    p = LI_PATH_TEST_MODE
    unlink(p) if exists(p) else pathlib.Path(p).touch()


def cb_graph_demo():
    p = TMP_PATH_GRAPH_TEST_MODE_JSON
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


def c_e():
    if os.path.exists(TMP_DDC_ERR):
        os.unlink(TMP_DDC_ERR)


def p_e(s):
    PC.R('[ DDC error ] ' + s)
    with open(TMP_DDC_ERR, 'a') as f:
        f.write(f'error: {s}\n')


def p_w(s):
    PC.Y('[ DDC warning ] ' + s)


def p_i(s):
    PC.B('[ DDC information ] ' + s)


def cb_calibrate_display():
    c = "export XAUTHORITY=/home/pi/.Xauthority; " \
        "export DISPLAY=:0; " \
        "xinput_calibrator"
    sh(c)
    # file has to be copied to
    # /etc/X11/xorg.conf.d/99-calibration.conf
    # todo --> detect bookworm vs bullseye, also move xorg file


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
str_i = ''


def ddh_run_check():

    global str_e
    global str_w
    global str_i
    str_e = ''
    str_w = ''
    str_i = ''

    def _e(s):
        global str_e
        str_e += f'   - {s}\n'

    def _i(s):
        global str_i
        str_i += f'   - {s}\n'

    def _w(s):
        global str_w
        str_w += f'   - {s}\n'

    def _check_fw_cell():
        ls = find_n_list_all_usb_port_automatically(VP_QUECTEL)
        # ls: ['/dev/ttyUSB3', '/dev/ttyUSB2', '/dev/ttyUSB1, '/dev/ttyUSB0']
        if not ls:
            _e('detecting cell shield gave 0 entries')
            return 0
        if len(ls) != 4:
            _e('detecting cell shield should have 4 entries')
            return 0

        version = ''
        for p in ls:
            till = time.perf_counter() + 1
            b = bytes()
            ser = None
            try:
                ser = serial.Serial(p, 115200, timeout=.1, rtscts=True, dsrdtr=True)
                ser.write(b'AT+CVERSION \rAT+CVERSION \r')
                while time.perf_counter() < till:
                    b += ser.read()
                ser.close()
                if b'VERSION' in b:
                    version = b.decode()
                    break
            except (Exception,) as ex:
                if ser and ser.isOpen():
                    ser.close()
                # print(f'error {p} -> {ex}')

        # check
        return '2022' in version

    def _check_aws_credentials():
        c = cfg_load_from_file()
        f = c['credentials']
        for k, v in f.items():
            if not v:
                if 'custom' not in k:
                    _e(f'config.toml no credential {k}')
                    # 0 is bad
                    return 0
                else:
                    _w(f'config.toml no custom credential {k}')
        if not check_aws_run(f):
            _e(f'config.toml AWS credentials cannot connect')
            return 0
        return 1

    def _check_files():
        path_w = '/etc/wireguard/wg0.conf'
        if is_rpi():
            c = f'sudo ls {path_w}'
            _rv = sp.run(c, shell=True, stdout=sp.PIPE, stderr=sp.PIPE)
            w = _rv.returncode == 0
        else:
            w = os.path.exists(path_w)
        a = os.path.exists(f'/home/pi/.ssh/authorized_keys')
        m = os.path.exists(f'{get_ddh_folder_path_settings()}/all_macs.toml')

        if not w:
            _w('missing wireguard VPN conf file')
        if not a:
            _i('missing SSH authorized keys file')
        if not m:
            _e('missing ddh/settings/all_macs.toml file')

    # -----------------------------------------------------
    # issue: Raspberry Pi reference 2023-05-03
    # is_rpi3: Raspberry Pi 3 Model B Plus Rev 1.3
    # hostname: raspberrypi
    # hardware flags
    # grep exact (-w) for 'active' detection
    # dwservice
    # -----------------------------------------------------
    ok_issue_20240315 = sh('cat /boot/issue.txt | grep 2024-03-15') == 0
    ok_issue_20230503 = sh('cat /boot/issue.txt | grep 2023-05-03') == 0
    ok_issue_20220922 = sh('cat /boot/issue.txt | grep 2022-09-22') == 0
    is_rpi3 = sh("cat /proc/cpuinfo | grep 'aspberry Pi 3'") == 0
    ok_hostname = sh('hostname | grep raspberrypi') == 0
    flag_gps_ext = sh(f'[ -f {LI_PATH_DDH_GPS_EXTERNAL} ]') == 0
    flag_vp_gps_puck1 = sh(f'lsusb | grep {VP_GPS_PUCK_1}') == 0
    flag_vp_gps_puck2 = sh(f'lsusb | grep {VP_GPS_PUCK_2}') == 0
    flag_vp_quectel = sh(f'lsusb | grep {VP_QUECTEL}') == 0
    flag_mod_btuart = sh(f'md5sum /usr/bin/btuart | grep {MD5_MOD_BTUART}') == 0
    ok_ble_v = sh('bluetoothctl -v | grep 5.66') == 0
    _c = 'systemctl is-active unit_switch_net.service | grep -w active'

    ts = time.perf_counter()
    ok_service_cell_sw = sh(_c) == 0
    if DEBUG_TIME:
        el_ts = time.perf_counter() - ts
        print(f'ok_service_cell_sw took {int(el_ts)}')

    ts = time.perf_counter()
    ok_fw_cell = _check_fw_cell()
    if DEBUG_TIME:
        el_ts = time.perf_counter() - ts
        print(f'_check_fw_cell took {int(el_ts)}')

    ts = time.perf_counter()
    ok_internet_via_cell = sh('timeout 1 ping -c 1 -I ppp0 www.google.com -4') == 0
    if DEBUG_TIME:
        el_ts = time.perf_counter() - ts
        print(f'ok_internet_via_cell took {int(el_ts)}')

    ok_dwservice = sh('ps -aux | grep dwagent') == 0

    ts = time.perf_counter()
    ok_aws_cred = _check_aws_credentials()
    if DEBUG_TIME:
        el_ts = time.perf_counter() - ts
        print(f'ok_aws_cred took {int(el_ts)}')

    ok_crontab_ddh = get_crontab('ddh') == 1
    ok_crontab_api = get_crontab('api') == 1
    ok_crontab_lxp = get_crontab('lxp') == 1
    ok_shield_j4h = cb_get_flag_j4h() == 1
    ok_shield_sailor = cb_get_flag_sailor() == 1

    ts = time.perf_counter()
    ok_keys = _check_files() == 0
    if DEBUG_TIME:
        el_ts = time.perf_counter() - ts
        print(f'ok_keys took {int(el_ts)}')

    # check conflicts
    rv = 0
    if not ok_keys:
        _i('not all keys OK')
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
    if not (ok_issue_20230503 or
            ok_issue_20220922 or
            ok_issue_20240315):
        _e('bad /boot/issue.txt file')
        rv += 1
    if not ok_hostname:
        _e('bad hostname')
        rv += 1
    if flag_gps_ext and not flag_vp_gps_puck1 and not flag_vp_gps_puck2:
        _e('GPS puck: set but not detected')
        rv += 1
    if is_rpi3 and not flag_mod_btuart:
        _e(f'is_rpi3 {is_rpi3}, bad mod_uart')
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
        _w('no hardware power shield present')
    return rv, str_e, str_w, str_i
