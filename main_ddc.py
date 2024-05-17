import os
import pathlib
import sys
import time
from os.path import exists
from scripts.script_ddc import (
    cb_gps_dummy, cb_quit, cb_gps_external, cb_crontab_ddh,
    get_crontab,
    cb_graph_demo, cb_provision_ddh,
    cb_kill_ddh, ddh_run_check, cb_calibrate_display, sh, cb_test_mode, is_rpi, VP_QUECTEL, p_w, p_e
)
from scripts.script_nadv import main_nadv
from utils.ddh_config import _get_config_file_path, cfg_load_from_file
from utils.ddh_shared import get_ddh_folder_path_settings
from utils.tmp_paths import (
    TMP_PATH_GPS_DUMMY,
    LI_PATH_DDH_GPS_EXTERNAL,
    TMP_PATH_GRAPH_TEST_MODE_JSON, LI_PATH_TEST_MODE
)
import subprocess as sp
from mat.utils import PrintColors as PC


# cwd() is ddh folder here
h = str(pathlib.Path.home())
p = 'li/ddh' if is_rpi() else 'PycharmProjects/ddh'
path_script_deploy_dox = f'{h}/{p}/scripts/run_script_deploy_logger_dox.sh'
path_script_deploy_tdo = f'{h}/{p}/scripts/run_script_deploy_logger_tdo.sh'


# variables for errors and warnings
g_e = None
g_w = None


def _ddh_show_issues_error():
    if g_e:
        p_e('\nErrors preventing DDH from starting:')
        p_e(g_e)


def _ddh_show_issues_warning():
    if g_w:
        p_w('\nPlease notice:')
        p_w(g_w)


def cb_ddh_show_issues():
    _ddh_show_issues_error()
    _ddh_show_issues_warning()
    input()


def cb_test_gps_quectel():
    try:
        if not is_rpi():
            p_e('no Rpi for GPS quectel test')
            return
        from scripts.script_test_gps_quectel import main_test_gps_quectel
        if sh(f'lsusb | grep {VP_QUECTEL}') == 0:
            main_test_gps_quectel()
        else:
            p_e('no GPS puck')
    except (Exception,) as ex:
        p_e(str(ex))


def cb_test_buttons():
    try:
        if not is_rpi():
            p_e('no Rpi for buttons test')
            return
        from scripts.script_test_box_buttons import main_test_box_buttons
        main_test_box_buttons()
    except (Exception,) as ex:
        p_e(str(ex))


def cb_run_brt():
    # pyc files are managed by "pop_ddh" script
    path_script_brt = f'{h}/{p}/scripts/main_brt_armv7l.pyc'
    sh(f'/usr/bin/env python3 {path_script_brt}')
    input()


def cb_run_nadv():
    main_nadv()


def cb_run_deploy_dox():
    try:
        # do this or this script's prompts fail
        sp.run(path_script_deploy_dox)
    except (Exception,) as ex:
        p_e(f'{ex} running deploy_dox')


def cb_run_deploy_tdo():
    try:
        # do this or this script's prompts fail
        sp.run(path_script_deploy_tdo)
    except (Exception,) as ex:
        p_e(f'{ex} running deploy_tdo')


def cb_edit_brt_cfg_file():
    sp.call(['nano', f'{h}/Downloads/cfg_brt_nadv.toml'],
            stdin=sys.stdin, stdout=sys.stdout)


def cb_edit_ddh_config_file():
    sp.call(['nano', _get_config_file_path()],
            stdin=sys.stdin, stdout=sys.stdout)


def _check_aws_credentials():
    c = cfg_load_from_file()
    f = c['credentials']
    for k, v in f.items():
        if not v:
            if 'custom' not in k:
                return 0
            else:
                return 1
    return 1


def cb_we_have_all_keys():
    have_file_wg = os.path.exists('/etc/wireguard/wg0.conf')
    have_file_au = os.path.exists(f'{h}/.ssh/authorized_keys')
    have_file_co = _check_aws_credentials()
    have_file_am = os.path.exists(f'{get_ddh_folder_path_settings()}/all_macs.toml')

    if have_file_wg and have_file_au and have_file_co and have_file_am:
        return 1

    return 0


def cb_is_ddh_running():
    rh = sp.run('ps aux | grep main_ddh | grep -v grep > /dev/null',
                shell=True).returncode == 0
    rs = sp.run('ps aux | grep main_dds | grep -v grep > /dev/null',
                shell=True).returncode == 0
    return int(rh and rs)


# --------------
# main DCC loop
# --------------

def main_ddc():
    while 1:
        os.system('clear')
        print('\nDDC\n---\n')

        # add extra one being displayed
        _, g_e, g_w = ddh_run_check()

        # get flags
        fgd = 1 if exists(TMP_PATH_GPS_DUMMY) else 0
        fge = 1 if exists(LI_PATH_DDH_GPS_EXTERNAL) else 0
        fcd = get_crontab('ddh')
        fgt = 1 if exists(TMP_PATH_GRAPH_TEST_MODE_JSON) else 0
        fdk = cb_we_have_all_keys()
        fdr = cb_is_ddh_running()
        ftm = 1 if exists(LI_PATH_TEST_MODE) else 0

        # create options
        d = {
            '0': (f"0) set test mode     [{ftm}]", cb_test_mode),
            '1': (f"1) set GPS dummy     [{fgd}]", cb_gps_dummy),
            '2': (f"2) set GPS puck      [{fge}]", cb_gps_external),
            '3': (f"3) set crontab       [{fcd}]", cb_crontab_ddh),
            '4': (f"4) kill DDH app      [{fdr}]", cb_kill_ddh),
            '5': (f"5) set graph demo    [{fgt}]", cb_graph_demo),
            '6': (f"6) test credentials  [{fdk}]", cb_we_have_all_keys),
            '7': (f"7) test GPS shield", cb_test_gps_quectel),
            '8': (f"8) test side buttons", cb_test_buttons),
            'r': (f"r) run BLE range tool", cb_run_brt),
            'e': (f"e) edit BLE range tool", cb_edit_brt_cfg_file),
            'o': (f"o) deploy logger DOX", cb_run_deploy_dox),
            't': (f"t) deploy logger TDO", cb_run_deploy_tdo),
            # 'c': (f"c) calibrate DDH display", cb_calibrate_display),
            'i': (f"i) ~ see issues ~", cb_ddh_show_issues),
            'q': (f"q) quit", cb_quit)
        }

        # show menu
        for k, v in d.items():
            if 'issues' in v[0]:
                if g_e:
                    PC.R(f'\t{v[0]}')
                elif g_w:
                    PC.W(f'\t{v[0]}')
            # normal entry
            else:
                print(f'\t{v[0]}')

        # get user input
        try:
            c = input('\nenter your choice > ')
            time.sleep(.5)

            # secret options
            if c == 'p':
                cb_provision_ddh()
            elif c == 'k':
                cb_edit_ddh_config_file()
            else:
                _, cb = d[c]
                cb()
        except (Exception,):
            continue


if __name__ == "__main__":
    main_ddc()
