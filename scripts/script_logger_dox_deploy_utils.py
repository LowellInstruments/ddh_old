import asyncio
import json
from bleak import BleakScanner, BleakError
from bleak.backends.device import BLEDevice
from mat.ble.bleak.cc26x2r import BleCC26X2
from mat.utils import PrintColors as PC

lc = BleCC26X2("hci0", dbg_ans=True)


def _e(_rv, s):
    if _rv:
        _ = "[ BLE ] example exception {}, rv {}"
        raise Exception(_.format(s, _rv))


def get_script_cfg_file():
    # here it is OK to crash to detect bad json files
    p = f"scripts/script_logger_dox_deploy_cfg.json"
    with open(p) as f:
        return json.load(f)


def set_script_cfg_file(cfg_d: dict):
    p = f"scripts/script_logger_dox_deploy_cfg.json"
    with open(p, "w") as f:
        return json.dump(cfg_d, f)


async def deploy_logger_dox(mac, sn, flag_run, flag_sensor):

    rv = 0

    try:
        rv = await lc.connect(mac)
        _e(rv, "connecting")

        # firmware version the first in case fails
        rv, v = await lc.cmd_gfv()
        _e(rv, "gfv")

        rv = await lc.cmd_stp()
        _e(rv, "stp")

        rv = await lc.cmd_led()
        _e(rv, "led")

        rv = await lc.cmd_sts()
        _e(rv[0], "sts")

        rv, t = await lc.cmd_gtm()
        _e(rv, "gtm")

        rv = await lc.cmd_stm()
        _e(rv, "stm")

        rv = await lc.cmd_frm()
        _e(rv, "frm")

        d = get_script_cfg_file()
        rv = await lc.cmd_cfg(d)
        _e(rv, "cfg")

        rv = await lc.cmd_wli("BA8007")
        _e(rv, "wli_ba")
        await asyncio.sleep(.1)

        rv = await lc.cmd_wli("MA1234ABC")
        _e(rv, "wli_ma")
        await asyncio.sleep(.1)

        rv = await lc.cmd_wli("CA1234")
        _e(rv, "wli_ca")
        await asyncio.sleep(.1)

        s = "SN{}".format(sn)
        rv = await lc.cmd_wli(s)
        _e(rv, "wli_sn")
        await asyncio.sleep(.1)

        rv, info = await lc.cmd_rli()
        _e(len(info.keys()) != 4, "rli")

        rv = await lc.cmd_wak("on")
        if rv:
            rv = await lc.cmd_wak("on")
        _e(rv, "wak")

        # these stand for First Deployment Get / Set on TDO loggers
        # rv, v = await lc.cmd_fdg()
        # _e(rv, 'fds')
        # rv, v = await lc.cmd_fds()
        # _e(rv, 'fds')
        # rv, v = await lc.cmd_fdg()
        # _e(rv, 'fdg')

        rv = await lc.cmd_gdo()
        print("\t\tGDO --> {}".format(rv))
        bad_rv = not rv or (rv and rv[0] == "0000")
        if flag_sensor:
            _e(bad_rv, "gdo")

        rv, b = await lc.cmd_bat()
        bad_rv = rv == 1
        _e(bad_rv, "bat")
        print("\t\tBAT | {} mV".format(b))

        # -------------------------------
        # RUNs logger, depending on flag
        # -------------------------------
        if flag_run:
            await asyncio.sleep(1)
            g = (1.111111, 2.222222, None, None)
            rv = await lc.cmd_rws(g)
            print("\t\tRWS --> {}".format(rv))
            _e(rv, "rws")

        else:
            print("\t\tRWS --> omitted: current flag value is False")

        # do not remove this
        rv = 0

    except (Exception,) as ex:
        print(PC.FAIL + "\t{}".format(ex) + PC.ENDC)
        rv = 1

    finally:
        await lc.disconnect()
        return rv


async def ble_scan_for_dox_loggers(t=5.0):

    _dd = {}
    _dl = []

    def _scan_cb(d: BLEDevice, adv_data):
        logger_types = ["DO-2", "DO-1"]
        if d.name in logger_types:
            _dd[d.address.lower()] = adv_data.rssi

    try:
        print(f"\nscanning for {int(t)} seconds for DOX loggers")
        scanner = BleakScanner(_scan_cb, None)
        await scanner.start()
        await asyncio.sleep(t)
        await scanner.stop()
        # _dl: [ (mac, rssi), (mac2, rssi), ...]
        _dl = [(k, v) for k, v in _dd.items()]
        return _dl

    except (asyncio.TimeoutError, BleakError, OSError) as ex:
        print("error BLE scan {}".format(ex))
        return []
