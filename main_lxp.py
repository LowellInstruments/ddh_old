#!/usr/bin/env python3

import subprocess as sp


NAME_EXE_LXP = "main_lxp"


def sh(c):
    rv = sp.run(c, shell=True, stdout=sp.PIPE, stderr=sp.PIPE)
    return rv


def is_rpi():
    return sh('cat /proc/cpuinfo | grep aspberry').returncode == 0


def main_lxp():
    if not is_rpi():
        return
    c = "ps -p $(pgrep -f lxpanel) -o %mem"
    rv = sh(c)
    print(rv.stdout)
    # c = 'sudo lxpanelctl restart'
    # sh(c)
    # print('restarting lxpanel, only works in graphical session')


if __name__ == "__main__":
    main_lxp()
