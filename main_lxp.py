#!/usr/bin/env python3

import subprocess as sp


NAME_EXE_LXP = "main_lxp"
LIMIT = 20


def sh(c):
    rv = sp.run(c, shell=True, stdout=sp.PIPE, stderr=sp.PIPE)
    return rv


def is_rpi():
    return sh('cat /proc/cpuinfo | grep aspberry').returncode == 0


def main_lxp():
    if not is_rpi():
        return

    # get pid of lxpanel
    pid = sh("pidof lxpanel").stdout.decode().replace('\n', '')
    if not pid:
        print('error: no pid for lxpanel, leaving')
        return

    # get used memory by lxpanel by using its PID
    print(f"lxpanel pid {pid}")
    rv = sh(f"ps -p {pid} -o %mem")
    s = rv.stdout.replace(b'%MEM\n', b'').decode()
    try:
        m = float(s)
    except (Exception,) as ex:
        print(f'error {NAME_EXE_LXP}: cannot get float -> {str(ex)}')
        return

    # display how much memory is using
    if m == 0:
        print(f'error {NAME_EXE_LXP}: mem 0 should not happen')
        return
    if m < LIMIT:
        print(f'{NAME_EXE_LXP} not consuming that much, leaving')
        return

    # kill lxpanel if too demanding
    print(f'{NAME_EXE_LXP} consuming > {LIMIT}% total RAM, restarting it')
    rv = sh('sudo lxpanelctl restart')
    if rv.returncode == 0:
        print('OK restarting lxpanel')
    else:
        print('error: main_lxp, only works on graphical session')


if __name__ == "__main__":
    main_lxp()