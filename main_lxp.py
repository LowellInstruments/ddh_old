#!/usr/bin/env python3

import subprocess as sp


EXE = "main_lxp"
LIMIT = 20
LOG_FILE = '/tmp/mem_lxpanel.log'


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
        print('error: no PID for lxpanel, bye')
        return

    # get used memory by lxpanel by using its PID
    print(f"lxpanel PID = {pid}")
    rv = sh(f"ps -p {pid} -o %mem")
    s = rv.stdout.replace(b'%MEM\n', b'').decode()
    try:
        m = float(s)
    except (Exception,) as ex:
        print(f'error {EXE}: cannot get float -> {str(ex)}')
        return

    # log the consumption that lead us to kill lxpanel
    sh(f"echo {m} >> {LOG_FILE}")

    # display how much memory is using
    if m == 0:
        print(f'error {EXE}: mem 0 should not happen')
        return
    if m < LIMIT:
        print(f'{EXE} uses {m} < limit {LIMIT}%, no need to restart')
        return

    # kill lxpanel
    print(f'{EXE} uses {m} > {LIMIT}% total RAM, restarting it')
    rv = sh('sudo lxpanelctl restart')
    sh(f"echo 'killed' >> {LOG_FILE}")
    if rv.returncode:
        # the exports in run_lxp.sh solve this
        print('error: main_lxp, only works on graphical session')


if __name__ == "__main__":
    main_lxp()
