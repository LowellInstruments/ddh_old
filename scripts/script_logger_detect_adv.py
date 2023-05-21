import asyncio
import sys
import time
from bleak import BleakScanner, BLEDevice, BleakError

REQ_COND_NAMES = True
ael = asyncio.new_event_loop()
asyncio.set_event_loop(ael)
_g_dd = {}


def _valid_name(s):
    if not REQ_COND_NAMES:
        return True
    return s.startswith('DO-') or \
           s.startswith('MAT') or \
           s.startswith('TAP')


def _summary():
    def _diff(tt):
        diff_tt = []
        for x, y in zip(tt[0::], tt[1::]):
            diff_tt.append(y - x)
        return diff_tt

    global _g_dd
    # sort it by mac
    _ = list(_g_dd.keys())
    _.sort()
    _g_dd = {i: _g_dd[i] for i in _}

    # calculate average
    for k, tt in _g_dd.items():
        if len(tt) > 1:
            d = _diff(tt)
            v = int((sum(d) / len(d)) * 1000)
            d = [float('{:.4f}'.format(i)) for i in d]
            print('\n{}\n{:<3} | {:>5} ms {}'.format(k, len(d), v, d[:10]))
        else:
            # len = 1 means no diffs
            print('\n{}\n*'.format(k))

    _g_dd = {}


async def ble_scan_mean_adv(t=10.0):

    if len(sys.argv) == 2:
        t = float(sys.argv[1])

    def _scan_cb(d: BLEDevice, _):
        try:
            s = str(d.name)
        except (Exception,):
            return

        if _valid_name(s):
            global _g_dd
            mac = d.address.lower()
            k = '{} {}'.format(mac, d.name)
            if k not in _g_dd.keys():
                _g_dd[k] = list()
            _g_dd[k].append(time.time())

    try:
        print("\nADV averager - scanning for {} seconds".format(int(t)))
        scanner = BleakScanner(_scan_cb, None)
        await scanner.start()
        await asyncio.sleep(t)
        await scanner.stop()
        _summary()

    except (asyncio.TimeoutError, BleakError, OSError) as ex:
        print("error BLE scan {}".format(ex))
        return []


if __name__ == '__main__':
    ael.run_until_complete(ble_scan_mean_adv())
