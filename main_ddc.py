import os
import pathlib
import sys
import time
from os.path import exists
from scripts.script_ddc import (
    cb_gps_dummy, cb_quit, cb_gps_external, cb_crontab_ddh,
    get_crontab,
    cb_graph_demo, cb_provision_ddh,
    cb_kill_ddh, ddh_run_check, cb_calibrate_display, sh, cb_test_mode, is_rpi, VP_QUECTEL, p_w, p_e, c_e, p_i
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
g_i = None


def _p(s):
    print(s)


def _ddh_show_issues_error():
    if g_e:
        p_e('\nthe following can prevent DDH from starting')
        PC.R(g_e)


def _ddh_show_issues_warning():
    if g_w:
        p_w('\nplease notice')
        PC.Y(g_w)


def _ddh_show_issues_info():
    if g_i:
        p_i('\nmiscellaneous info')
        PC.B(g_i)


def cb_ddh_show_issues():
    _ddh_show_issues_error()
    _ddh_show_issues_warning()
    _ddh_show_issues_info()
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
    c = '/home/pi/li/ddh/run_brt.sh'
    rv = sp.run(c, shell=True, stderr=sp.PIPE, stdout=sp.PIPE)
    if rv.returncode:
        print('BRT error: {rv.stderr}')
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
    p_cfg = f'{h}/Downloads/cfg_brt_nadv.toml'
    if not os.path.exists(p_cfg):
        sp.run(f'cp scripts/cfg_brt_nadv_template.toml {p_cfg}')
    sp.call(['nano', p_cfg],
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


def cb_print_check_all_keys(verbose=True):
    path_w = '/etc/wireguard/wg0.conf'
    if is_rpi():
        c = f'sudo ls {path_w}'
        rv = sp.run(c, shell=True, stdout=sp.PIPE, stderr=sp.PIPE)
        w = rv.returncode == 0
    else:
        w = os.path.exists(path_w)
    a = os.path.exists(f'{h}/.ssh/authorized_keys')
    c = _check_aws_credentials()
    m = os.path.exists(f'{get_ddh_folder_path_settings()}/all_macs.toml')

    rv = w and a and c and m

    if rv:
        return rv

    if verbose and not w:
        p_e('missing wireguard conf file')
    if verbose and not a:
        p_i('missing SSH authorized keys file')
    if verbose and not c:
        p_e('missing ddh/settings/config.toml credentials section')
    if verbose and not m:
        p_e('missing ddh/settings/all_macs.toml file')

    if verbose:
        input()
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


def cb_ddh_show_help():
    _p('test mode    -> prefixes downloaded filenames with "testfile_"')
    _p('GPS dummy    -> GPS is simulated, it uses position in config.toml')
    _p('GPS puck     -> GPS source is a USB GPS puck, not a RPi shield')
    _p('crontab      -> automatically starts or not DDH app upon boot')
    _p('kill DDH     -> forces DDH app to quit')
    _p('graph demo   -> the DDH plotting tab will use simulated data')
    _p('credentials  -> checks the DDH has all the passwords to run OK')
    _p('GPS shield   -> tests the GPS shield, not the GPS puck')
    _p('side buttons -> tests the DDH real side buttons to be working')
    _p('BLE range    -> tests how well a logger\'s signal reaches the DDH')
    _p('MAC range    -> sets the MAC address used in BLE range')
    _p('deploy DOX   -> prepares a DO-1 or DO-2 logger for deployment')
    _p('deploy TDO   -> prepares a TDO logger for deployment')
    # _p('calibrate    -> tunes the DDH touch display')
    _p('see issues   -> check any potential DDH conflict or misconfiguration')
    input()


def main_ddc():

    # clearing error log file
    c_e()

    while 1:
        os.system('clear')
        print('\nDDC\n---')

        # -------------------------
        # check everything at once
        # -------------------------
        global g_e
        global g_w
        global g_i
        _, g_e, g_w, g_i = ddh_run_check()

        # get flags
        fgd = 1 if exists(TMP_PATH_GPS_DUMMY) else 0
        fge = 1 if exists(LI_PATH_DDH_GPS_EXTERNAL) else 0
        fcd = get_crontab('ddh')
        fgt = 1 if exists(TMP_PATH_GRAPH_TEST_MODE_JSON) else 0
        fdk = cb_print_check_all_keys(verbose=False)
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
            '6': (f"6) check all keys    [{fdk}]", cb_print_check_all_keys),
            '7': (f"7) test GPS shield", cb_test_gps_quectel),
            '8': (f"8) test side buttons", cb_test_buttons),
            'r': (f"r) run BLE range tool", cb_run_brt),
            'e': (f"e) edit BLE range tool", cb_edit_brt_cfg_file),
            'o': (f"o) deploy logger DOX", cb_run_deploy_dox),
            't': (f"t) deploy logger TDO", cb_run_deploy_tdo),
            # 'c': (f"c) calibrate DDH display", cb_calibrate_display),
            'i': (f"i) ~ see issues ~", cb_ddh_show_issues),
            'h': (f"h) help", cb_ddh_show_help),
            'q': (f"q) quit", cb_quit)
        }

        # show menu
        for k, v in d.items():
            if 'issues' in v[0]:
                # color of the 'see issues' entry
                if g_e:
                    PC.R(f'\t{v[0]}')
                elif g_w:
                    PC.Y(f'\t{v[0]}')
                elif g_i:
                    PC.B(f'\t{v[0]}')

            # normal entry
            else:
                print(f'\t{v[0]}')

        # get user input
        c = input('\nenter your choice > ')
        try:
            os.system('clear')
            print(f'you selected:\n\t{d[c][0]}')
            time.sleep(1)

            # secret options
            if c == 'p':
                cb_provision_ddh()
            elif c == 'k':
                cb_edit_ddh_config_file()
            else:
                _, cb = d[c]
                cb()

        except (Exception,):
            p_e(f'invalid menu option {c}')
            time.sleep(1)


if __name__ == "__main__":
    main_ddc()
