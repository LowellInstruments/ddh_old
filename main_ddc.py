import os
import sys
from os.path import exists
from scripts.script_ddc import (
    cb_gps_dummy, cb_quit, cb_gps_external, cb_crontab_ddh,
    get_crontab,
    cb_graph_test_mode, cb_provision_ddh,
    cb_kill_ddh, ddh_run_check, cb_calibrate_display, sh
)
from utils.ddh_config import _get_config_file_path
from utils.tmp_paths import (
    TMP_PATH_GPS_DUMMY,
    LI_PATH_DDH_GPS_EXTERNAL,
    TMP_PATH_GRAPH_TEST_MODE_JSON
)
import subprocess as sp
from mat.utils import PrintColors as PC


g_e = None
g_w = None


def _ddh_show_issues_error():
    if g_e:
        PC.R('\nThere are errors preventing DDH from start')
        print(PC.R(g_e))


def _ddh_show_issues_warning():
    if g_w:
        print('\nPlease consider:')
        print(g_w)


def cb_ddh_show_issues():
    _ddh_show_issues_error()
    _ddh_show_issues_warning()
    input()


def cb_edit_ddh_config_file():
    sp.call(['nano', _get_config_file_path()],
            stdin=sys.stdin, stdout=sys.stdout)


if __name__ == "__main__":

    while 1:
        os.system('clear')
        print('\nDDC\n---')

        # add extra one being displayed
        _, g_e, g_w = ddh_run_check()

        # get flags
        fgd = 1 if exists(TMP_PATH_GPS_DUMMY) else 0
        fge = 1 if exists(LI_PATH_DDH_GPS_EXTERNAL) else 0
        fcd = get_crontab('ddh')
        ftm = 1 if exists(TMP_PATH_GRAPH_TEST_MODE_JSON) else 0
        fdk = False  # todo--> check if we have all keys
        fdr = False  # todo ---> now if DDH is running

        # create options
        d = {
            0: (f"0) set test mode  [{ftm}]", cb_graph_test_mode),
            1: (f"1) set GPS dummy  [{fgd}]", cb_gps_dummy),
            2: (f"2) set GPS puck   [{fge}]", cb_gps_external),
            3: (f"3) set crontab    [{fcd}]", cb_crontab_ddh),
            4: (f"4) kill DDH app   [{fdr}]", cb_kill_ddh),
        }

        # keep index of new stuff to add
        i = len(d)

        # add extra one being displayed
        if sh('arch | grep aarch64') == 0:
            d[i] = (f"{i}) calibrate DDH display", cb_calibrate_display)
            i += 1

        # add extra one being displayed
        d[i] = (f"{i}) === DDH issues ===", cb_ddh_show_issues)

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
            c = int(input('\nenter your choice > '))
            # secret options
            if c == 'p':
                cb_provision_ddh()
            elif c == 'e':
                cb_edit_ddh_config_file()
            else:
                _, cb = d[c]
                cb()
        except (Exception,):
            continue
