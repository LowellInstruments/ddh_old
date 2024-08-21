#!/usr/bin/env python3


import asyncio
import sys
import subprocess as sp
import os
import time

import toml

from mat.utils import PrintColors as PC, linux_is_rpi
from script_logger_tdo_deploy_utils import (
    deploy_logger_tdo,
    ble_scan_for_tdo_loggers,
)


# don't move this from here
FILE_ALL_MACS_TOML = f'../settings/all_macs.toml'


# ---------------------------------
# issues RUN command or not at end
# ---------------------------------
g_cfg = {
    "RUN": False,
    "DFN": 'TST',
    "PRF": 'script_logger_tdo_deploy_cfg_slow.json',
}


def get_ddh_toml_all_macs_content():
    try:
        with open(FILE_ALL_MACS_TOML, 'r') as f:
            # d: {'11:22:33:44:55:66': 'sn1234567'}
            return toml.load(f)
    except (Exception,) as ex:
        print('error: get_ddh_toml_all_macs_content: ', ex)
        os._exit(1)


def _screen_clear():
    sp.run("clear", shell=True)


def _screen_separation():
    print("\n\n")


def _menu_get():
    return input("\t-> ")


def _list_all_macs_file_content():
    ls_macs = get_ddh_toml_all_macs_content()
    if not ls_macs:
        return

    print("\nmonitored macs\n--------------\n")
    for i, (k, v) in enumerate(ls_macs.items()):
        if k.startswith("#") or len(k) < 5:
            continue
        print(f'{i}) {k} SN{v}')


def _menu_build(_sr: dict, n: int):

    ddh_d = get_ddh_toml_all_macs_content()
    if not ddh_d:
        e = "error -> all_macs list is empty"
        print(PC.FAIL + e + PC.ENDC)
        return
    # convert to lower-case
    ddh_d = dict((k.lower(), v) for k, v in ddh_d.items())

    # --------------------------------------------------
    # filters scan results: only MACS in our dictionary
    # --------------------------------------------------
    d = {}
    i = 0
    for each_sr in _sr:
        mac, rssi = each_sr
        if mac not in ddh_d:
            continue

        # --------------------------------------------------------
        # builds menu of up to 'n' entries d[#i]: (mac, sn, rssi)
        # --------------------------------------------------------
        sn = str(ddh_d[mac])
        d[i] = (mac, sn, rssi)
        i += 1
        if i == n - 1:
            break

    return d


def _menu_display(d: dict):
    print("scan done!")
    print("\nchoose an option:")
    print("\ts) scan for loggers nearby")
    print("\tl) list monitored macs in config.toml file")
    print(f"\tr) toggle RUN flag, current value is {g_cfg['RUN']}")
    print(f"\td) set DEPLOYMENT, current value is {g_cfg['DFN']}")
    print(f"\tp) toggle PROFILING file, now is {g_cfg['PRF'].split('_cfg_')[1]}")
    print("\tq) quit")
    if not d:
        return

    # print found macs with number
    for k, v in d.items():
        s = "\t{}) deploy {} -> SN {} -> rssi {}"
        print(s.format(k, v[0], v[1], v[2]))


ael = asyncio.new_event_loop()
asyncio.set_event_loop(ael)


def _menu_execute(_m, _c):

    # _c: user choice
    if _c == "q":
        print("bye!")
        sys.exit(0)

    if _c == "s":
        # re-scan
        return

    if _c == "l":
        _list_all_macs_file_content()
        return

    if _c == "r":
        g_cfg['RUN'] = not g_cfg['RUN']
        return

    if _c == "p":
        _p = g_cfg["PRF"]
        if 'slow' in _p:
            _p = 'script_logger_tdo_deploy_cfg_mid.json'
        elif 'mid' in _p:
            _p = 'script_logger_tdo_deploy_cfg_fast.json'
        elif 'fast' in _p:
            _p = 'script_logger_tdo_deploy_cfg_slow.json'
        g_cfg["PRF"] = _p
        return

    if _c == "d":
        # ------------------------
        # set new deployment name
        # ------------------------
        i = str(input("\t\t enter new deployment -> "))
        if len(i) != 3:
            print("invalid input: must be 3 letters long")
            return
        g_cfg["DFN"] = i
        return

    # --------------------------------------------
    # safety check, logger menu keys are integers
    # --------------------------------------------
    if not str(_c).isnumeric():
        print(PC.WARNING + "\tunknown option" + PC.ENDC)
        return
    _c = int(_c)
    if _c >= len(_m):
        print(PC.WARNING + "\tbad option" + PC.ENDC)
        return

    # safety check, SN length
    mac, sn = _m[_c][0], _m[_c][1]
    if len(sn) != 7:
        e = "\terror: got {}, but serial numbers must be 7 digits long"
        print(PC.FAIL + e.format(sn) + PC.ENDC)
        return

    # =====================================
    # call main routine logger preparation
    # =====================================
    print(PC.OKBLUE + "\n\tdeploying logger {}...".format(mac) + PC.ENDC)
    rv = ael.run_until_complete(deploy_logger_tdo(mac, sn, g_cfg))

    # show green or red success
    _ = "\n\t========================"
    s_ok = PC.OKGREEN + _ + "\n\tsuccess {}" + _ + PC.ENDC
    s_nok = PC.FAIL + _ + "\n\terror {}" + _ + PC.ENDC
    s = s_ok if rv == 0 else s_nok
    print(s.format(mac))


def main_logger_tdo_deploy():
    _screen_clear()
    print(f'TDO_deploy current folder: {os.getcwd()}')

    while True:
        sr = ael.run_until_complete(ble_scan_for_tdo_loggers())
        m = _menu_build(sr, 10)
        _menu_display(m)
        c = _menu_get()
        _menu_execute(m, c)
        _screen_separation()


if __name__ == "__main__":
    if not linux_is_rpi():
        # Pycharm, be sure starting directory is 'ddh/scripts'
        assert str(os.getcwd()).endswith('scripts')
    main_logger_tdo_deploy()
