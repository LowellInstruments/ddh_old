#!/usr/bin/env python
import os
import sys

# -------------------------------------------------
# this script runs on a laptop
# probably as root because of mounting disks
# it creates a provision bootstrap file
# and saves it in the recently cloned DDH SSD disk
# -------------------------------------------------


PRJ = 'abc'
DEV = ''


def main():
    os.system('clear')

    # check root access
    if os.geteuid() != 0:
        print('error: script PBF must be run as root')
        sys.exit(1)

    print("let's create the provision bootstrap file")
    ip = input("ip:\n")
    sn = input("boat sn:\n")
    prj = PRJ or input("prj:\n")
    dev = DEV or input("dev:\n")
    dev = f'/dev/{dev}'
    print(ip, sn, prj, dev)
    # todo ---> create file /home/pi/.ddh_prov_req.toml

    # copy the file to the destination disk
    # todo ---> detect harddisks with auto-port
    # todo ---> mount harddisk
    # todo ---> copy created toml file

    # todo ---> start wireguard and also ENABLE at boot


if __name__ == '__main__':
    main()
