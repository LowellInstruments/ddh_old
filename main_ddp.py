import os
import pathlib
import subprocess as sp
import sys
import time


VP_QUECTEL = '2c7c:0125'


def sh(cmd):
    rv = sp.run(cmd, shell=True, stdout=sp.PIPE, stderr=sp.PIPE)
    if rv.returncode:
        print(rv.stderr)
    return rv.returncode


def is_rpi():
    return sh('cat /proc/cpuinfo | grep aspberry') == 0


# cwd() is ddh folder here
h = str(pathlib.Path.home())
p = 'li/ddh' if is_rpi() else 'PycharmProjects/ddh'
path_script_deploy_dox = f'{h}/{p}/scripts/run_script_deploy_logger_dox.sh'
path_script_deploy_tdo = f'{h}/{p}/scripts/run_script_deploy_logger_tdo.sh'

# these pyc files are managed by pop_ddh.sh
path_script_brt = f'{h}/{p}/scripts/main_brt.pyc'
path_script_nadv = f'{h}/{p}/scripts/main_nadv.pyc'


def _e(e):
    print(f'DDP error: {e}')
    time.sleep(3)


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
    sh(f'/usr/bin/env python3 {path_script_brt}')


def cb_run_nadv():
    # call it like this or we don't see output
    sp.call(['python3', path_script_nadv],
            stdin=sys.stdin, stdout=sys.stdout)


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

        # create options
        d = {
            0: ("0) test GPS shield", cb_test_gps_quectel),
            1: ("1) test side buttons", cb_test_buttons),
            2: ("2) run BLE range tool", cb_run_brt),
            3: ("3) deploy logger DOX", cb_run_deploy_dox),
            # 4: ("4) deploy logger TDO", cb_run_deploy_tdo),
            9: ("9) quit", cb_quit)
        }

        # show the menu
        for i in d.values():
            print(f'\t{i[0]}')

        # get user input
        try:
            c = int(input('\nenter your choice > '))
            # secret one
            if c == 'n':
                cb_run_nadv()
            else:
                _, cb = d[c]
                cb()
        except (Exception, ):
            continue
