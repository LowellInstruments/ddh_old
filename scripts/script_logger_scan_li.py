#!/usr/bin/env python3


import asyncio
import sys
import subprocess as sp
import os
import toml

from mat.utils import PrintColors as PC
from script_logger_dox_deploy_utils import (
    set_script_cfg_file,
    deploy_logger_dox,
    get_script_cfg_file,
    ble_scan_for_dox_loggers,
)
from scripts.script_logger_tdo_deploy_utils import ble_scan_for_tdo_loggers

# don't move this from here
FILE_ALL_MACS_TOML = f'../settings/all_macs.toml'


# ---------------------------------
# issues RUN command or not at end
# ---------------------------------
g_flag_run = False
g_flag_sensor = True


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


ael = asyncio.new_event_loop()
asyncio.set_event_loop(ael)


def main():
    _screen_clear()
    d_macs_sn = get_ddh_toml_all_macs_content()
    print(d_macs_sn)
    d_macs_sn = {k.lower(): v for k, v in d_macs_sn.items()}

    sr = ael.run_until_complete(ble_scan_for_dox_loggers())
    for i in sr:
        mac, rssi = i
        mac = mac.lower()
        if mac in d_macs_sn.keys():
            sn = d_macs_sn[mac]
            print(f'{mac}\t{sn}\t{rssi}')
        else:
            print(f'{mac}\t_______\t{rssi}')

    sr = ael.run_until_complete(ble_scan_for_tdo_loggers())
    for i in sr:
        mac, rssi = i
        mac = mac.lower()
        if mac in d_macs_sn.keys():
            sn = d_macs_sn[mac]
            print(f'{mac}\t{sn}\t {rssi}')
        else:
            print(f'{mac}\t_______\t {rssi}')


if __name__ == "__main__":
    main()
