#!/usr/bin/env python3


import time
import subprocess as sp


IP = '8.8.8.8'


def _p(s):
    print(s)


def _sh(s: str) -> bool:
    rv = sp.run(s, shell=True, stdout=sp.PIPE, stderr=sp.PIPE)
    return rv.returncode == 0


g_debug = 0


def main():

    wlan_via = _sh(f'timeout 1 ping -c 1 -I wlan0 www.google.com -4')
    wlan_used = _sh(f'ip route get {IP} | grep wlan0')

    if wlan_via and wlan_used:
        _p('wifi')
        return

    cell_via = _sh(f'timeout 1 ping -c 1 -I ppp0 www.google.com -4')
    cell_used = _sh(f'ip route get {IP} | grep ppp0')

    if cell_via and cell_used:
        _p('cell')
        return

    _p('.')


if __name__ == '__main__':
    while 1:
        main()
        time.sleep(5)
