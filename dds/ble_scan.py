import asyncio
from dds.sqs import sqs_msg_ddh_error_ble_hw
from dds.timecache import its_time_to
from settings import ctx
from utils.ddh_shared import (
    send_ddh_udp_gui as _u,
    dds_get_macs_from_json_file,
    STATE_DDS_BLE_SCAN_FIRST_EVER,
    STATE_DDS_BLE_SCAN, STATE_DDS_BLE_HARDWARE_ERROR,
)
from bleak import BleakScanner, BleakError
from bleak.backends.device import BLEDevice
from utils.logs import lg_dds as lg


PERIOD_BLE_TELL_HW_ERR_SECS = 600
_g_first_ble_scan_ever = True
_g_json_macs = dds_get_macs_from_json_file()


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

    # classify devs
    _our_devs = {}
    _all_devs = {}
    _ble_scan_banner(_h, _h_desc)

    # yep, simulated scan hook
    if ctx.hook_ble_scan_cc26x2r_sim:
        return {"11:22:33:44:55:66": "DO-2"}

    try:
        # convert hci format integer to string
        ad = "hci{}".format(_h)
        scanner = BleakScanner(_scan_cb, None, adapter=ad)
        await scanner.start()
        await asyncio.sleep(t)
        await scanner.stop()

        # do not stress BLE
        await asyncio.sleep(1)

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
