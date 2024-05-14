import os
import pathlib
import sys
import time
from os.path import exists
from scripts.script_ddc import (
    cb_gps_dummy, cb_quit, cb_gps_external, cb_crontab_ddh,
    get_crontab,
    cb_graph_demo, cb_provision_ddh,
    cb_kill_ddh, ddh_run_check, cb_calibrate_display, sh, cb_test_mode
)
from utils.ddh_config import _get_config_file_path, cfg_load_from_file
from utils.ddh_shared import get_ddh_folder_path_settings
from utils.tmp_paths import (
    TMP_PATH_GPS_DUMMY,
    LI_PATH_DDH_GPS_EXTERNAL,
    TMP_PATH_GRAPH_TEST_MODE_JSON, LI_PATH_TEST_MODE
)
import subprocess as sp
from mat.utils import PrintColors as PC


h = str(pathlib.Path.home())
g_e = None
g_w = None


def _ddh_show_issues_error():
    if g_e:
        PC.R('\nErrors preventing DDH from starting:')
        PC.R(g_e)


def _ddh_show_issues_warning():
    if g_w:
        PC.Y('\nPlease notice:')
        PC.Y(g_w)


def cb_ddh_show_issues():
    _ddh_show_issues_error()
    _ddh_show_issues_warning()
    input()


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

    if have_file_wg and have_file_au and \
        have_file_co and have_file_am:
        return 1

    return 0


def cb_is_ddh_running():
    c = 'ps aux | grep main_ddh | grep -v grep > /dev/null'
    rh = sp.run(c, shell=True).returncode == 0
    c = 'ps aux | grep main_dds | grep -v grep > /dev/null'
    rs = sp.run(c, shell=True).returncode == 0
    return int(rh and rs)


if __name__ == "__main__":

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
            0: (f"0) set test mode  [{ftm}]", cb_test_mode),
            1: (f"1) set GPS dummy  [{fgd}]", cb_gps_dummy),
            2: (f"2) set GPS puck   [{fge}]", cb_gps_external),
            3: (f"3) set crontab    [{fcd}]", cb_crontab_ddh),
            4: (f"4) kill DDH app   [{fdr}]", cb_kill_ddh),
            5: (f"5) set graph demo [{fgt}]", cb_graph_demo),
            6: (f"6) know all keys  [{fdk}]", cb_we_have_all_keys)
        }

        # keep index of new stuff to add
        i = len(d)

        # add extra one being displayed
        if sh('arch | grep aarch64') == 0:
            d[i] = (f"{i}) calibrate DDH display", cb_calibrate_display)
            i += 1

        # add extra one being displayed
        d[i] = (f"{i}) ~ see issues ~", cb_ddh_show_issues)

        # keep order
        d[9] = (f"9) quit", cb_quit)

        # show menu
        for k, v in d.items():
            if 'issues' in v[0]:
                PC.R(f'\t{v[0]}')
            else:
                print(f'\t{v[0]}')

        # get user input
        try:
            c = input('\nenter your choice > ')
            time.sleep(.5)

            # secret options
            if c == 'p':
                cb_provision_ddh()
            elif c == 'e':
                cb_edit_ddh_config_file()
            else:
                _, cb = d[int(c)]
                cb()
        except (Exception,):
            continue
