import asyncio
import json
from bleak import BleakScanner, BleakError
from bleak.backends.device import BLEDevice
from mat.ble.bleak.cc26x2r import BleCC26X2
from mat.utils import PrintColors as PC
from utils.ddh_shared import ddh_get_root_folder_path


lc = BleCC26X2("hci0", dbg_ans=True)


_r = ddh_get_root_folder_path()


def _e(_rv, s):
    if _rv:
        _ = "[ BLE ] example exception {}, rv {}"
        raise Exception(_.format(s, _rv))


async def deploy_logger_tdo(mac, sn, cfg):

    rv = 0

    try:
        rv = await lc.connect(mac)
        _e(rv, "connecting")

        # firmware version the first in case fails
        rv, v = await lc.cmd_gfv()
        _e(rv, "gfv")

        g = ("-3.333333", "-4.444444", None, None)
        rv = await lc.cmd_sws(g)
        _e(rv, "sws")

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

        #rv = await lc.cmd_wak("on")
        #if rv:
        #    rv = await lc.cmd_wak("on")
        #_e(rv, "wak")

        # these stand for First Deployment Get / Set on TDO loggers
        rv, v = await lc.cmd_fdg()
        _e(rv, 'fdg')
        rv = await lc.cmd_fds()
        _e(rv, 'fds')
        rv, v = await lc.cmd_fdg()
        _e(rv, 'fdg')

        rv, b = await lc.cmd_bat()
        bad_rv = rv == 1
        _e(bad_rv, "bat")
        print("\t\tBAT | {} mV".format(b))

        # -------------------------------------
        # profiling mode set
        # -------------------------------------
        prf_json_file = cfg['PRF']
        with open(prf_json_file) as f:
            # file to dict
            j_i = json.load(f)
            print(f'SCF: loaded {prf_json_file}')

            # flash SCF into logger
            for tag, v in j_i.items():
                if len(tag) != 3:
                    print(f'error: bad SCF tag {tag}')
                    break
                if len(v) != 5:
                    print(f'error: bad SCF value {v} for tag {tag}')
                    break

                # send the SCF command
                rv = await lc.cmd_scf(tag, v)
                bad_rv = rv == 1
                _e(bad_rv, f"scf {tag}")

        # -------------------------------
        # RUNs logger, depending on flag
        # -------------------------------
        if cfg['RUN']:
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


async def ble_scan_for_tdo_loggers(t=5.0):

    _dd = {}
    _dl = []

    def _scan_cb(d: BLEDevice, adv_data):
        logger_types = ["TDO", ]
        if d.name in logger_types:
            _dd[d.address.lower()] = adv_data.rssi

    try:
        print(f"\nscanning for {int(t)} seconds for TDO loggers")
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
