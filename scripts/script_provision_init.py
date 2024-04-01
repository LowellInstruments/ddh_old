#!/usr/bin/env python

import os
import sys
import subprocess as sp


# -------------------------------------------------
# this script  creates a provision bootstrap file
# and saves it in the recently cloned DDH SSD disk
# -------------------------------------------------


PRJ = 'abc'
DEV = ''


def sh(c):
    rv = sp.run(c, shell=True, stdout=sp.PIPE, stderr=sp.PIPE)
    return rv.returncode


def is_rpi():
    return sh('cat /proc/cpuinfo | grep aspberry') == 0


def main():
    # checks
    os.system('clear')
    if is_rpi():
        print('let\'s not run this on a raspberry but a laptop')
        sys.exit(1)
    if not DEV or '/dev/' not in DEV:
        print(f'error: bad destination dev -> ({DEV})')
        sys.exit(1)
    if os.geteuid() != 0:
        print('error: script_provision_init must run as root')
        sys.exit(1)

    print("let's create the provision bootstrap file")
    ip = input("ip:\n")
    sn = input("boat sn:\n")
    prj = PRJ or input("prj:\n")
    dev = DEV or input("dev:\n")
    dev = f'/dev/{dev}'
    print(ip, sn, prj, dev)
    # todo ---> create file /home/pi/.ddh_prov_req.toml
    # todo ---> mount harddisk and copy created toml file
    # todo ---> create file FLAG_CLONED_BALENA = '/home/pi/.ddh_cloned_w_balena'
    # todo ---> unmount disk


if __name__ == '__main__':
    main()
