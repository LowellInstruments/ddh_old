import os
from datetime import datetime

from mat import data_file_factory
from mat.ble.bleak.rn4020 import BleRN4020
from utils.ddh_shared import (
    send_ddh_udp_gui as _u,
    STATE_DDS_REQUEST_PLOT,
    get_dl_folder_path_from_mac,
    create_folder_logger_by_mac,
)
from settings.ctx import BLEAppException, ael
from utils.logs import lg_dds as lg


def _rae(rv, s):
    if rv:
        raise BLEAppException("rn4020 interact " + s)


class BleRN4020Download(BleRN4020):
    async def download_recipe(self, mac, h, g):
        rv = await self.connect(mac)
        _rae(rv, "connecting")
        lg.a("connected to {}".format(mac))

        # RN4020 has SWS command but no RWS
        if g:
            # putting SWS in gps file is done by MAT library
            rv = await self.cmd_sws(g)
            _rae(rv, "sws")
            lg.a("SWS | OK")
        else:
            _rae(1, "sws")

        rv = await self.cmd_btc()
        _rae(rv, "btc")
        lg.a("BTC | OK")

        rv, v = await self.cmd_gfv()
        _rae(rv, "gfv")
        lg.a("GFV | {}".format(v))

        rv, v = await self.cmd_gtm()
        _rae(rv, "gtm")
        lg.a("GTM | {}".format(v))
        rv = await self.cmd_stm()
        _rae(rv, "stm")
        lg.a("STM | OK")

        rv, ls = await self.cmd_dir()
        _rae(rv, "dir error " + str(rv))
        lg.a("DIR | {}".format(ls))

        any_dl = False
        for name, size in ls.items():

            # skip non-interesting files
            if name.endswith(".cfg"):
                continue
            if name.endswith(".lis"):
                continue
            if name.startswith("Archive"):
                continue
            if "Trash" in name:
                continue

            # download file
            lg.a("getting file {}".format(name))
            rv = await self.cmd_get(name)
            _rae(rv, "get")

            # dynamically resolved to method in class BleRN4020
            lg.a("xmodem file {}".format(name))
            rv, data = await self.cmd_xmodem(size)
            _rae(rv, "xmodem")

            # save file in our local disk
            path = str(get_dl_folder_path_from_mac(mac) / name)
            create_folder_logger_by_mac(mac)
            with open(path, "wb") as f:
                f.write(data)

            # grab the file's CLK header section
            try:
                _ = data_file_factory.load_data_file(path)
                t = _.header().tag("CLK")
                t = t.replace(":", "")
                t = t.replace("-", "")
                t = t.replace(" ", "")
                # t: 20230217171119, YYYYMMDDHHMMSS
                t = t[:8] + "_" + t[8:]
                dst = path.replace(".lid", "")
                dst = "{}_{}.lid".format(dst, t)
                os.rename(path, dst)
            except (Exception, ) as ex:
                e = "error after downloading RN4020 -> {}"
                lg.a(e.format(ex))

            # delete file in logger
            lg.a("deleting file {}".format(name))
            rv = await self.cmd_del(name)
            _rae(rv, "del")
            any_dl = True

        # RN4020 has no RWS
        rv = await self.cmd_run()
        _rae(rv, "run")
        lg.a("RUN | OK")

        # bluetooth bye
        await self.cli.disconnect()

        # plots
        if any_dl:
            _u("{}/{}".format(STATE_DDS_REQUEST_PLOT, mac))

        return 0


async def ble_interact_rn4020(mac, info, g, h):
    lc = BleRN4020Download(h, verbose=False)

    try:
        s = "interacting with RN4020 logger, info {}"
        lg.a(s.format(info))
        rv = await lc.download_recipe(mac, h, g)
        return rv

    except Exception as ex:
        print("[ BLE ] dl_rn4020_exception", ex)
        await lc.disconnect()
        return 1


# test, creates an extra inner 'dl_files' folder
if __name__ == "__main__":
    _m = "00:1E:C0:4D:BF:DB"
    _i = "MATP-2W"
    _g = ("+1.111111", "-2.222222", datetime.now(), 0)
    _h = "hci0"
    _args = [_m, _i, _g, _h]
    ael.run_until_complete(ble_interact_rn4020(*_args))
