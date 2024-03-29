#!/usr/bin/env python3

import subprocess as sp
import sys

from mat.ble.ble_mat_utils import ble_mat_get_bluez_version
from utils.ddh_config import cfg_load_from_file
from utils.tmp_paths import (LI_PATH_DDH_GPS_EXTERNAL,
                             TMP_PATH_GPS_DUMMY)

vp_rb = '0403:6001'
vp_quectel = '2c7c:0125'
vp_gps_puck_1 = '067B:2303'
vp_gps_puck_2 = '067B:23A3'
vp_ssd = '045b:0229'
FLAG_CLONED_BALENA = '/home/pi/.ddh_cloned_w_balena'
MD5_OF_MODIFIED_BTUART = '95da1d6d0bea327aa5426b7f90303778'


def _fw_cell():
    c = "echo -ne 'AT+CVERSION\r' > /dev/ttyUSB2"
    _sh(c)
    c = "cat -v < /dev/ttyUSB2 | grep 2022"
    return _sh(c)


def _e(s):
    print('\n*****')
    print(f'error: {s}')
    print('*****')
    sys.exit(1)


def _w(s):
    print('\n~~~~~')
    print(f'warning: {s}')
    print('~~~~~\n')


def _sh(c):
    _rv = sp.run(c, shell=True, stdout=sp.PIPE, stderr=sp.PIPE)
    # print('rv_rc', _rv.returncode)
    # print('rv_ou', _rv.stdout)
    # print('rv_er', _rv.stderr)
    return _rv.returncode, _rv.stdout.decode().replace('\n', '')


# issue: Raspberry Pi reference 2023-05-03
_, issue_2023_05_03 = _sh('cat /boot/issue.txt | grep 2023-05-03')
# arch: armv7l
_, arch_armv7l = _sh('arch | grep armv7l')
# is_rpi3:  Model		: Raspberry Pi 3 Model B Plus Rev 1.3
_, is_rpi3 = _sh("cat /proc/cpuinfo | grep 'aspberry Pi 3'")
_, is_rpi4 = _sh("cat /proc/cpuinfo | grep 'aspberry Pi 4'")
# hostname: raspberrypi
_, hostname = _sh('hostname | grep raspberrypi')
# flags are 0 or 1
rv_clone_balena, _ = _sh(f'[ ! -f {FLAG_CLONED_BALENA} ]')
rv_gps_external, _ = _sh(f'[ ! -f {LI_PATH_DDH_GPS_EXTERNAL} ]')
rv_vp_gps_puck1, _ = _sh(f'lsusb | grep {vp_gps_puck_1}')
rv_vp_gps_puck2, _ = _sh(f'lsusb | grep {vp_gps_puck_2}')
rv_gps_dummy, _ = _sh(f'[ ! -f {TMP_PATH_GPS_DUMMY} ]')
# disk: Bus 001 Device 004: ID 045b:0229 Hitachi, Ltd mSATA...
_, disk_ssd = _sh(f'lsusb | grep {vp_ssd}')
_, mod_btuart = _sh(f'md5sum /usr/bin/btuart | grep {MD5_OF_MODIFIED_BTUART}')
cfg = cfg_load_from_file()
rbl_en = int(cfg['flags']['rbl_en'])
ble_v = ble_mat_get_bluez_version()
_, service_cell_sw = _sh(f'systemctl is-active unit_switch_net.service')
_, fw_cell = _fw_cell()


def run_check():
    if not fw_cell:
        _e(f'bad fw_cell {fw_cell}')
    if not rv_clone_balena:
        _w('box NOT cloned with balena')
    if rv_gps_dummy:
        _w(f'GPS dummy active, file {TMP_PATH_GPS_DUMMY}')
    if service_cell_sw != 'active':
        _e(f'bad service_cell_sw {service_cell_sw}')
    if ble_v != '5.66':
        _e(f'bad ble_v {ble_v}')
    if not issue_2023_05_03:
        _e(f'bad issue {issue_2023_05_03}')
    if not arch_armv7l:
        _e(f'bad arch {arch_armv7l}')
    if not hostname:
        _e(f'bad hostname {hostname}')
    if rv_gps_external and not rv_vp_gps_puck1 and not rv_vp_gps_puck2:
        _e(f'rv_gps_external {rv_gps_external}, file {LI_PATH_DDH_GPS_EXTERNAL}')
    if is_rpi3 and not mod_btuart:
        _e(f'is_rpi3 {is_rpi3} mod_uart {mod_btuart}')
    if rbl_en and not vp_rb:
        _e(f'rbl_en {rbl_en} vp_rb {vp_rb}')

    print('\n[ OK ] all checks\n')
