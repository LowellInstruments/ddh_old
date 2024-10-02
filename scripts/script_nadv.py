import asyncio
import pathlib
import subprocess as sp
import sys
import time

import toml
import numpy as np
from bleak import BleakScanner
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData
from bleak.backends.bluezdbus.scanner import BlueZDiscoveryFilters, BlueZScannerArgs


def sh(c):
    rv = sp.run(c, shell=True, stdout=sp.PIPE, stderr=sp.PIPE)
    return rv.returncode


def is_rpi():
    return sh('cat /proc/cpuinfo | grep aspberry') == 0


h = pathlib.Path.home()
PATH_CFG = f'{h}/Downloads/cfg_brt_nadv.toml'


g_d = dict()


async def _main_nadv(sm=''):
    def simple_callback(device: BLEDevice, advertisement_data: AdvertisementData):
        mac = device.address
        # if '' in advertisement_data:
        #     return
        # sm: searched mac
        if sm and mac != sm:
            return
        if sm:
            print('*', end='')
        if mac not in g_d.keys():
            g_d[mac] = {}
            # n: num of ADV
            g_d[mac]['n'] = 1
            # c: calculated ADV rate in seconds
            g_d[mac]['c'] = 0
            # d: dBm list
            g_d[mac]['d'] = list()
            # m: mean dBm
            g_d[mac]['m'] = 0
        else:
            g_d[mac]['n'] += 1
        g_d[mac]['d'].append(advertisement_data.rssi)

    # useful when we run this as a loop to reset counter
    global g_d
    g_d = {}

    # scan
    filters = BlueZDiscoveryFilters(Transport="le", DuplicateData=True)
    scanner = BleakScanner(simple_callback, bluez=BlueZScannerArgs(filters=filters))
    t = 10.0
    print(f'scanning for {t} s.')
    if sm:
        print(f'searched mac {sm}')
    await scanner.start()
    await asyncio.sleep(t)
    await scanner.stop()

    # aesthetics
    if sm:
        print('')

    for k, v in g_d.items():
        g_d[k]['c'] = '{:.2f}'.format(t / g_d[k]['n'])
        g_d[k]['m'] = int(np.mean(g_d[k]['d']))
        s = f"\n{k}\n"
        s += f"\t{g_d[k]['n']} pkt -> ADV {g_d[k]['c']} s.\n"
        s += f"\t{g_d[k]['m']} dBm\n"
        # s += f"\t{g_d[k]['d']} dBm\n"
        print(s)

    print('\n')


def main_nadv(hc_mac=''):
    if not hc_mac:
        try:
            with open(PATH_CFG, 'r') as f:
                cfg = toml.load(f)
                _sm = cfg['cfg_nadv']['mac']
        except (Exception, ) as ex:
            print(ex)
            print('see file example in settings folder')
            time.sleep(2)
            sys.exit(1)
    else:
        _sm = hc_mac

    while 1:
        asyncio.run(_main_nadv(sm=_sm))


if __name__ == '__main__':
    m = 'D0:2E:AB:D9:29:48'
    main_nadv(m)
