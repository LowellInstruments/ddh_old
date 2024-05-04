import os
from os.path import exists
from scripts.script_ddc import (
    cb_gps_dummy, cb_quit, cb_gps_external, cb_crontab_ddh,
    get_crontab,
    cb_graph_test_mode, cb_provision_ddh,
    cb_kill_ddh, ddh_run_check, cb_calibrate_display, sh
)
from utils.tmp_paths import (
    TMP_PATH_GPS_DUMMY,
    LI_PATH_DDH_GPS_EXTERNAL,
    TMP_PATH_GRAPH_TEST_MODE_JSON
)


def _ddh_show_issues_error(e):
    if e:
        # todo ---> print red
        print('errors preventing DDH from start')
        print(e)


def _ddh_show_issues_warning(w):
    if w:
        print('DDH not so serious errors')
        print(w)


def cb_ddh_show_issues(e, w):
    _ddh_show_issues_error(e)
    _ddh_show_issues_warning(w)


if __name__ == "__main__":
    while 1:
        os.system('clear')
        print('\nDDC\n---')

        # get flags
        fgd = 1 if exists(TMP_PATH_GPS_DUMMY) else 0
        fge = 1 if exists(LI_PATH_DDH_GPS_EXTERNAL) else 0
        fcd = get_crontab('ddh')
        ftm = 1 if exists(TMP_PATH_GRAPH_TEST_MODE_JSON) else 0
        fdk = False  # todo--> check if we have all keys
        fdr = False  # todo ---> now if DDH is running

        d = {
            f"0) set test mode  [{ftm}]": (0, cb_graph_test_mode),
            f"1) set GPS dummy  [{fgd}]": (1, cb_gps_dummy),
            f"2) set GPS puck   [{fge}]": (2, cb_gps_external),
            f"3) set crontab    [{fcd}]": (3, cb_crontab_ddh),
            f"4) provision keys [{fdk}]": (4, cb_provision_ddh),
            f"5) kill DDH app   [{fdr}]": (5, cb_kill_ddh),
        }

        # add extra one being displayed
        if sh('arch | grep aarch64') == 0:
            d["7) calibrate DDH display"] = (7, cb_calibrate_display)

        # add extra one being displayed
        rv, e, w = ddh_run_check()
        if rv:
            d["8) === see DDH issues ==="] = (8, cb_ddh_show_issues(e, w))

        # keep order
        d["9) quit"] = (9, cb_quit)

        # show menu
        for i in d.keys():
            print(f'\t{i}')
        ls_idx = [i[0] for i in d.values()]

        # get user input
        try:
            c = int(input('\nenter your choice > '))
        except (Exception,):
            continue
        if c not in ls_idx:
            continue
        cb = list(d.values())[c]

        # cb: (3, cb_see_ddh_issues)
        cb[1]()

