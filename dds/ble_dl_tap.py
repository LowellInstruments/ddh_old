import asyncio
import datetime
import os
from ddh.utils_graph import graph_set_fol_req_file
from dds.lef import dds_create_file_lef
from mat.ble.ble_mat_utils import (
    ble_mat_crc_local_vs_remote,
    DDH_GUI_UDP_PORT,
)
from mat.ble.bleak.cc26x2r import BleCC26X2
from dds.ble_utils_dds import ble_get_cc26x2_recipe_file_rerun_flag, ble_logger_ccx26x2r_needs_a_reset
from utils.ddh_shared import (
    send_ddh_udp_gui as _u,
    STATE_DDS_BLE_LOW_BATTERY,
    STATE_DDS_BLE_RUN_STATUS, STATE_DDS_BLE_ERROR_RUN, STATE_DDS_REQUEST_GRAPH,
)
from utils.logs import lg_dds as lg
from utils.ddh_shared import (
    get_dl_folder_path_from_mac,
    create_folder_logger_by_mac,
    STATE_DDS_REQUEST_PLOT,
)
from settings.ctx import BLEAppException, ael


def _rae(rv, s):
    if rv:
        raise BLEAppException("TAP interact " + s)


class BleTAPDownload:
    @staticmethod
    async def download_recipe(lc, mac, info, g, notes):

        # initialize variables
        notes["battery_level"] = 0xFFFF
        rerun_flag = ble_get_cc26x2_recipe_file_rerun_flag()
        create_folder_logger_by_mac(mac)

        rv = await lc.connect(mac)
        _rae(rv, "connecting")
        lg.a("connected to {}".format(mac))

        if ble_logger_ccx26x2r_needs_a_reset(mac):
            await lc.cmd_rst()
            # out of here for sure
            raise BLEAppException("cc26x2 interact logger reset file")

        rv = await lc.cmd_sws(g)
        _rae(rv, "sws")
        lg.a("SWS | OK")

        rv, t = await lc.cmd_utm()
        _rae(rv, "utm")
        lg.a("UTM | {}".format(t))

        rv, b = await lc.cmd_bat()
        _rae(rv, "bat")
        lg.a("BAT | {} mV".format(b))
        notes["battery_level"] = b
#         if b < 1800:
#             # give time to GUI to display
#             _u("{}/{}".format(STATE_DDS_BLE_LOW_BATTERY, mac))
#             await asyncio.sleep(3)
#
        rv, v = await lc.cmd_gfv()
        _rae(rv, "gfv")
        lg.a("GFV | {}".format(v))

        rv, v = await lc.cmd_gtm()
        _rae(rv, "gtm")
        lg.a("GTM | {}".format(v))

        rv = await lc.cmd_stm()
        _rae(rv, "stm")
        lg.a("STM | OK")

        rv, ls = await lc.cmd_dir()
        _rae(rv, "dir error " + str(rv))
        lg.a("DIR | {}".format(ls))

        # iterate files present in logger
        any_dl = False
        for name, size in ls.items():

            # delete zero-bytes files
            if size == 0:
                rv = await lc.cmd_del(name)
                _rae(rv, "del")
                continue

            # download file
            lg.a("downloading file {}".format(name))
            rv = await lc.cmd_dwg(name)
            _rae(rv, "dwg")
            up = DDH_GUI_UDP_PORT
            rv, d = await lc.cmd_dwl(int(size), ip="127.0.0.1", port=up)
            _rae(rv, "dwl")
            file_data = lc.ans

            # calculate crc
            path = "/tmp/ddh_crc_file"
            with open(path, "wb") as f:
                f.write(lc.ans)
            rv, r_crc = await lc.cmd_crc(name)
            _rae(rv, "crc")
            rv, l_crc = ble_mat_crc_local_vs_remote(path, r_crc)
            if (not rv) and os.path.exists(path):
                e = "error: bad CRC so removing local file {}"
                lg.a(e.format(path))
                os.unlink(path)

            # save file in our local disk
            path = str(get_dl_folder_path_from_mac(mac) / name)
            with open(path, "wb") as f:
                f.write(file_data)
            lg.a("downloaded file {}".format(name))

            # delete file in logger
            rv = await lc.cmd_del(name)
            _rae(rv, "del")
            any_dl = True
            lg.a("deleted file {}".format(name))

            # create LEF file with download info
            # todo ---> test this
            lg.a("creating file LEF for {}".format(name))
            dds_create_file_lef(g, name)

        # format file-system
        rv = await lc.cmd_frm()
        _rae(rv, "frm")
        lg.a("FRM | OK")

        # check sensors measurement
        # rv = await lc.cmd_gst()
        # rv = await lc.cmd_gsp()
        # rv = await lc.cmd_acc()
        # rv = await lc.cmd_gdo()
        # bad_rv = not rv or (rv and rv[0] == "0000")
        # if bad_rv:
        #     lg.a("GDO | error {}".format(rv))
        #     _u(STATE_DDS_BLE_DOWNLOAD_ERROR_GDO)
        #     await asyncio.sleep(5)
        # _rae(bad_rv, "gdo")
        # lg.a("GDO | {}".format(rv))

#         # wake mode
#         if rerun_flag:
#             rv = await lc.cmd_wak("on")
#         else:
#             rv = await lc.cmd_wak("off")
#         _rae(rv, "wak")
#         lg.a("WAK | OK")
#
        if rerun_flag:
            rv = await lc.cmd_rws(g)
            if rv:
                _u(STATE_DDS_BLE_ERROR_RUN)
                await asyncio.sleep(5)
            _rae(rv, "rws")
            lg.a("RWS | OK")
        else:
            # GUI telling this
            _u("{}/{}".format(STATE_DDS_BLE_RUN_STATUS, "off"))
            # give time to GUI to display
            await asyncio.sleep(5)

        # -----------------------
        # bye, bye to this logger
        # -----------------------
        await lc.disconnect()

        # plots
        if any_dl:
            _u("{}/{}".format(STATE_DDS_REQUEST_PLOT, mac))

        # for the new graphing engine
        # graph_set_fol_req_file(mac)
        # _u(STATE_DDS_REQUEST_GRAPH)

        return 0


async def ble_interact_tap(mac, info, g, h):

    notes = {}
    lc = BleCC26X2(h)

    try:
        # -------------------------
        # BLE connection done here
        # -------------------------
        s = "interacting with TAP logger, info {}"
        lg.a(s.format(info))
        rv = await BleTAPDownload.download_recipe(lc, mac, info, g, notes)

    except Exception as ex:
        lg.a("error dl_tap_exception {}".format(ex))
        rv = 1

    finally:
        return rv, notes


# ------
# test
# ------
if __name__ == "__main__":
    # _m = '60:77:71:22:C9:E8'
    _m = "11:22:33:44:55:66"
    _i = "DO-2"
    _g = ("+1.111111", "-2.222222", datetime.datetime.now(), 0)
    _h = "hci0"
    _args = [_m, _i, _g, _h]
    ael.run_until_complete(ble_interact_tap(*_args))
