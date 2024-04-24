import os
import pathlib
import subprocess as sp
import sys
import time


VP_QUECTEL = '2c7c:0125'


def _e(e):
    print(f'DDP error: {e}')
    time.sleep(3)


def sh(c):
    rv = sp.run(c, shell=True, stdout=sp.PIPE, stderr=sp.PIPE)
    if rv.returncode:
        print(rv.stderr)
    return rv.returncode


def is_rpi():
    return sh('cat /proc/cpuinfo | grep aspberry') == 0


# cwd is ddh here
h = str(pathlib.Path.home())
p = 'li/ddh' if is_rpi() else 'PycharmProjects/ddh'
path_script_deploy_dox = f'{h}/{p}/scripts/run_script_deploy_logger_dox.sh'
path_script_deploy_tdo = f'{h}/{p}/scripts/run_script_deploy_logger_tdo.sh'
path_script_brt = f'{h}/{p}/scripts/main_brt.pyc'
path_script_nadv = f'{h}/{p}/scripts/main_nadv.pyc'


def cb_test_gps_quectel():
    try:
        if not is_rpi():
            _e('no Rpi for GPS quectel test')
            return
        from scripts.script_test_gps_quectel import main_test_gps_quectel
        if sh(f'lsusb | grep {VP_QUECTEL}') == 0:
            main_test_gps_quectel()
        else:
            _e('no GPS puck')
    except (Exception, ) as ex:
        _e(str(ex))


def cb_test_buttons():
    try:
        if not is_rpi():
            _e('no Rpi for buttons test')
            return
        from scripts.script_test_box_buttons import main_test_box_buttons
        main_test_box_buttons()
    except (Exception, ) as ex:
        _e(str(ex))


def cb_run_brt():
    c = f'/usr/bin/env python {path_script_brt}'
    sh(c)


def cb_run_nadv():
    c = f'/usr/bin/env python {path_script_nadv}'
    sh(c)


def cb_run_deploy_dox():
    try:
        # do this or this script's prompts fail
        sp.run(path_script_deploy_dox)
    except (Exception, ) as ex:
        _e(f'{ex} running deploy_dox')


def cb_run_deploy_tdo():
    try:
        # do this or this script's prompts fail
        sp.run(path_script_deploy_tdo)
    except (Exception, ) as ex:
        _e(f'{ex} running deploy_tdo')


def cb_quit():
    sys.exit(0)


if __name__ == "__main__":
    while 1:
        os.system('clear')
        print('\nDDP\n---')
        d = {
            "0) test GPS shield": (0, cb_test_gps_quectel),
            "1) test side buttons": (1, cb_test_buttons),
            "2) run BLE range tool": (2, cb_run_brt),
            "3) run BLE n_adv tool": (3, cb_run_nadv),
            "4) deploy logger DOX": (4, cb_run_deploy_dox),
            "5) deploy logger TDO": (5, cb_run_deploy_tdo),
            "6) quit": (6, cb_quit)
        }
        for i in d.keys():
            print(f'\t{i}')
        ls_idx = [i[0] for i in d.values()]
        try:
            c = int(input('\nenter your choice > '))
        except (Exception, ):
            continue
        if c not in ls_idx:
            continue
        cb = list(d.values())[c]
        # (3, cb_run_deploy_tdo)
        cb[1]()
    print(d.keys())

