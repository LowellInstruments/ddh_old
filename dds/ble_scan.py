import asyncio
from math import ceil

from bleak.assigned_numbers import AdvertisementDataType
from bleak.backends.bluezdbus.advertisement_monitor import OrPattern

from dds.sqs import sqs_msg_ddh_error_ble_hw
from dds.timecache import its_time_to
from mat.ble.ble_mat_utils import ble_mat_get_bluez_version
from settings import ctx
from utils.ddh_shared import (
    send_ddh_udp_gui as _u,
    dds_get_macs_from_json_file,
    STATE_DDS_BLE_SCAN_FIRST_EVER,
    STATE_DDS_BLE_SCAN, STATE_DDS_BLE_HARDWARE_ERROR,
)
from bleak import BleakScanner, BleakError
from bleak.backends.bluezdbus.scanner import BlueZScannerArgs
from bleak.backends.device import BLEDevice
from utils.logs import lg_dds as lg


PERIOD_BLE_TELL_HW_ERR_SECS = 600
_g_first_ble_scan_ever = True
_g_json_macs = dds_get_macs_from_json_file()
_g_ble_scan_early_leave = False


# to activate BLE experimental features you need:
# bluez >= v5.65
# sudo nano /lib/systemd/system/bluetooth.service
# ExecStart=/usr/local/libexec/bluetooth/bluetoothd --experimental
_g_use_ble_exp = False

# see https://github.com/hbldh/bleak/issues/1433
_gbv = ble_mat_get_bluez_version()
_g_ble_scan_mode = "passive" if _gbv >= '5.65' else "active"
if _g_use_ble_exp:
    lg.a(f'bluez v.{_gbv} -> BLE scan mode {_g_ble_scan_mode}')


def _ble_is_supported_logger(s):
    logger_types = [
        "DO-2",
        "DO-1",
        "MOANA",
        "MAT-2W",
        "MATP-2W",
        "TAP1"
    ]
    for t in logger_types:
        if t in s:
            return True


def _ble_scan_banner(_h, _h_desc):

    global _g_first_ble_scan_ever
    if _g_first_ble_scan_ever:
        _u(STATE_DDS_BLE_SCAN_FIRST_EVER)
        _g_first_ble_scan_ever = False

    _u(STATE_DDS_BLE_SCAN)


async def ble_scan(g, _h: int, _h_desc, t=5.0):
    """
    SCANs for loggers, quits fast if all found
    """

    def _scan_cb(d: BLEDevice, _):
        if _ble_is_supported_logger(d.name):
            _our_devs[d.address.lower()] = d.name
        _all_devs[d.address.lower()] = d.name
        # allows scan to end faster
        global _g_ble_scan_early_leave
        _g_ble_scan_early_leave = len(_our_devs) == len(_g_json_macs)

    # classify devs
    _our_devs = {}
    _all_devs = {}
    _ble_scan_banner(_h, _h_desc)

    # yep, simulated scan hook
    if ctx.hook_ble_scan_cc26x2r_sim:
        return {"11:22:33:44:55:66": "DO-2"}

    try:
        # trick to go faster
        _g_ble_scan_early_leave = False

        # convert hci format integer to string
        ad = "hci{}".format(_h)

        # we need some research and activate this :)
        if _g_use_ble_exp:
            # https://github.com/hbldh/bleak/issues/1433
            args = BlueZScannerArgs(
                or_patterns=[OrPattern(0, AdvertisementDataType.COMPLETE_LOCAL_NAME, b"ZT-MOANA"),
                             OrPattern(0, AdvertisementDataType.COMPLETE_LOCAL_NAME, b"TAP1"),
                             OrPattern(0, AdvertisementDataType.COMPLETE_LOCAL_NAME, b"DO-1"),
                             OrPattern(0, AdvertisementDataType.COMPLETE_LOCAL_NAME, b"DO-2"),
                             ]
            )
            scanner = BleakScanner(_scan_cb, None, adapter=ad,
                                   scanning_mode=_g_ble_scan_mode,
                                   bluez=args)
        else:
            scanner = BleakScanner(_scan_cb, None, adapter=ad)

        # start scanning procedure
        await scanner.start()
        for i in range(ceil(t) * 10):
            # * 10 to be able to sleep 100 ms
            await asyncio.sleep(.1)
            if _g_ble_scan_early_leave:
                break
        await scanner.stop()

        # do not stress BLE
        await asyncio.sleep(.1)

        # _our_devs: {'60:77:71:22:ca:6d': 'DO-2', ...}
        if len(_all_devs) > 15:
            s = "warning: detected crowded BLE environment"
            if its_time_to(s, t=3600 * 6):
                lg.a(s)
        return _our_devs

    except (asyncio.TimeoutError, BleakError, OSError) as ex:
        _lat, _lon, _dt, _ = g
        e = "hardware error during scan! {}"
        if its_time_to(e, 600):
            lg.a(e.format(ex))
            sqs_msg_ddh_error_ble_hw(_lat, _lon)
            _u(STATE_DDS_BLE_HARDWARE_ERROR)
        return {}
