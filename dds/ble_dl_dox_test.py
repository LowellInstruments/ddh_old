import asyncio
import datetime
import os
from dds.lef import dds_create_file_lef
from dds.notifications import notify_logger_error_sensor_oxygen, notify_logger_error_low_battery, LoggerNotification
from mat.ble.ble_mat_utils import (
    ble_mat_crc_local_vs_remote,
    DDH_GUI_UDP_PORT, ble_mat_disconnect_all_devices_ll,
)
from mat.ble.bleak.cc26x2r import BleCC26X2
from mat.ble.bleak.cc26x2r_sim import BleCC26X2Sim, ble_logger_is_cc26x2r_simulated
from dds.ble_utils_dds import ble_logger_ccx26x2r_needs_a_reset, dds_ble_init_rv_notes
from utils.ddh_config import dds_get_cfg_logger_sn_from_mac
from utils.ddh_shared import (
    send_ddh_udp_gui as _u,
    STATE_DDS_BLE_LOW_BATTERY,
    STATE_DDS_BLE_RUN_STATUS, STATE_DDS_BLE_DOWNLOAD_ERROR_GDO,
    STATE_DDS_BLE_ERROR_RUN, BLEAppException, ael, get_ddh_rerun_flag_li,
)
from utils.logs import lg_dds as lg
from utils.ddh_shared import (
    get_dl_folder_path_from_mac,
    create_folder_logger_by_mac,
)
import json


MC_FILE = "MAT.cfg"


def _une(rv, notes, e, ce=0):
    # une: update notes error
    if not rv:
        return
    notes["error"] = "error " + str(e)
    notes["crit_error"] = int(ce)


def _rae(rv, s):
    if rv:
        raise BLEAppException("cc26x2 interact " + s)


class BleCC26X2Download:
    @staticmethod
    async def download_recipe(lc, mac, g, notes: dict):

        _is_a_lid_v2_logger = False
        sn = dds_get_cfg_logger_sn_from_mac(mac)

        rv = await lc.connect(mac)
        _une(rv, notes, "comm.")
        _rae(rv, "connecting")
        lg.a(f"connected to {mac}")

        # STOP with STRING
        rv = await lc.cmd_sws(g)
        _rae(rv, "sws")
        lg.a("SWS | OK")

        # to know if this DO-X logger uses LID or LIX files
        rv = await lc.cmd_xod()
        _is_a_lid_v2_logger = rv == 0
        lg.a(f"XOD | LIX {_is_a_lid_v2_logger}")

        # see if the DO sensor works
        # for i_do in range(3):
        #     rv = await lc.cmd_gdo()
        #     bad_rv = not rv or (rv and rv[0] == "0000")
        #     if not bad_rv:
        #         # good!
        #         lg.a("GDO | {}".format(rv))
        #         break
        #     # GDO went south, check number of retries remaining
        #     lg.a(f"GDO | error {rv}")
        #     if i_do == 2:
        #         _une(bad_rv, notes, "ox_sensor_error", ce=1)
        #         _rae(bad_rv, "gdo")
        #     else:
        #         _u(STATE_DDS_BLE_DOWNLOAD_ERROR_GDO)
        #         _une(bad_rv, notes, "ox_sensor_error", ce=0)
        #     await asyncio.sleep(5)

        # see if this guy has GDX (better GDO) instruction
        await asyncio.sleep(1)
        rv = await lc.cmd_gdx()
        bad_rv = rv and rv[0] == "0.00"
        _une(bad_rv, notes, "ox_sensor_error", ce=1)
        _rae(bad_rv, "gdx")
        lg.a(f"GDX | (beta) {rv}")
        await asyncio.sleep(1)

        # -----------------------
        # bye, bye to this logger
        # -----------------------
        await lc.disconnect()
        return 0


async def ble_interact_do1_or_do2_test(mac, info, g, h):

    rv = 0
    notes = {}
    lc = BleCC26X2(h)

    try:
        # -------------------------
        # BLE connection done here
        # -------------------------
        lg.a(f"TEST interacting with DO logger: {info}")
        rv = await BleCC26X2Download.download_recipe(lc, mac, g, notes)

    except Exception as ex:
        await lc.disconnect()
        lg.a(f"error dl_cc26x2r_exception {ex}")
        rv = 1

    finally:
        return rv, notes


# ------
# test
# ------
if __name__ == "__main__":
    # we currently in 'ddh/dds'
    ble_mat_disconnect_all_devices_ll()
    os.chdir('..')
    # joaquim
    # _m = "60:77:71:22:CA:6A"
    # 28
    _m = "D0:2E:AB:D8:C4:20"
    _i = "DO-2"
    _g = ("+1.111111", "-2.222222", datetime.datetime.now(), 0)
    _h = "hci0"
    _args = [_m, _i, _g, _h]
    ael.run_until_complete(ble_interact_do1_or_do2_test(*_args))
