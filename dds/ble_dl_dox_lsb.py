from dds.gpq import gpq_create_fixed_mode_file
from dds.lef import lef_create_file
from dds.notifications_v2 import *
from dds.state import state_ble_init_rv_notes, state_ble_logger_ccx26x2r_needs_a_reset
from lsb.cmd import *
from lsb.connect import *
from lsb.li import UUID_S, UUID_T
from lsb.utils import DDH_GUI_UDP_PORT
from utils.ddh_config import (
    dds_get_cfg_logger_sn_from_mac,
    dds_get_cfg_flag_download_test_mode,
    ddh_get_cfg_gear_type
)
from utils.ddh_shared import (
    BLEAppException, create_folder_logger_by_mac,
    get_dl_folder_path_from_mac,
    send_ddh_udp_gui as _u,
    STATE_DDS_BLE_LOW_BATTERY, TESTMODE_FILENAMEPREFIX,
    get_ddh_do_not_rerun_flag_li,
    STATE_DDS_BLE_ERROR_RUN, STATE_DDS_BLE_DOWNLOAD_ERROR_GDO,
)
from utils.logs import lg_dds as lg


MC_FILE = "MAT.cfg"
BAT_FACTOR_DOT = 0.4545


# une: update notes error
def _une(notes, e, ce=0):
    if get_rx():
        return
    notes["error"] = "error " + str(e)
    notes["crit_error"] = int(ce)


# rae: raise app exception
def _rae(s):
    if get_rx():
        return
    raise BLEAppException("DOX interact LSB: " + s)


def _dl_logger_dox_lsb(mac, g, notes: dict, u, hs):

    state_ble_init_rv_notes(notes)
    create_folder_logger_by_mac(mac)
    sn = dds_get_cfg_logger_sn_from_mac(mac)

    # get internal / external adapters
    ads = get_adapters()
    ad_i = int(hs[-1])
    ad = ads[ad_i]
    lg.a(f'using LSB with antenna #{ad_i}')

    # scan
    ad.set_callback_on_scan_found(cb_scan)
    pp = scan_for_peripherals(ad, 10000, mac)
    found, p_i = is_mac_in_found_peripherals(pp, mac)
    if not found:
        _une(notes, "scan")
        _rae(f"mac {mac} during scanning")

    # connect
    p = pp[p_i]
    if not connect_mac(p, mac):
        _une(notes, "comm.")
        _rae("connecting")
    lg.a(f"connected to {mac}")

    # configure notification
    p.notify(UUID_S, UUID_T, cb_rx_noti)

    if state_ble_logger_ccx26x2r_needs_a_reset(mac):
        cmd_rst(p)
        # out of here for sure
        raise BLEAppException("DOX interact logger reset file")

    v = cmd_xod(p)
    _is_a_lid_v2_logger = bool(v)
    lg.a(f"XOD | LIX {_is_a_lid_v2_logger}")

    v = cmd_gfv(p)
    _rae("gfv")
    lg.a(f"GFV | {v}")
    notes['gfv'] = v[6:].decode()

    v = cmd_sts(p)
    _rae("sts")
    lg.a(f"STS | logger was {v}")

    cmd_sws(p, g)
    _rae("sws")
    lg.a("SWS | OK")

    rv = cmd_utm(p)
    _rae("utm")
    lg.a(f"UTM | {rv}")

    b = cmd_bat(p)
    _rae("bat")
    adc_b = b
    b /= BAT_FACTOR_DOT
    lg.a(f"BAT | ADC {adc_b} mV -> battery {int(b)} mV")
    notes["battery_level"] = b
    if adc_b < 1500:
        ln = LoggerNotification(mac, sn, 'DOX', adc_b)
        ln.uuid_interaction = u
        notify_logger_error_low_battery(g, ln)
        _u(f"{STATE_DDS_BLE_LOW_BATTERY}/{mac}")
        # give time to GUI to display
        time.sleep(3)

    v = cmd_gtm(p)
    _rae("gtm")
    lg.a(f"GTM | {v}")

    rv = cmd_stm(p)
    _rae("stm")
    lg.a("STM | OK")

    # disable log for lower power consumption
    v = cmd_log(p)
    _rae("log")
    v = v.decode()[-1]
    if linux_is_rpi():
        if v != '0':
            cmd_log(p)
            _rae("log")
    else:
        # we want logs while developing
        if v != '1':
            cmd_log(p)
            _rae("log")

    ls = cmd_dir(p)
    _rae("dir error " + str(rv))
    ls = ls['ls']
    lg.a(f"DIR | {ls}")
    if MC_FILE not in ls.keys():
        _rae("error: no MAT.cfg file in DOX logger")

    # iterate files present in logger
    for name, size in ls.items():
        # delete zero-bytes files
        if size == 0:
            cmd_del(p, name)
            _rae("del")
            continue

        # targeting file to download
        lg.a(f"downloading file {name}")
        cmd_dwg(p, name)
        _rae("dwg")
        up = DDH_GUI_UDP_PORT
        dl_t = time.perf_counter()

        # download normal
        # file_data = cmd_dwl(p, int(size), ip="127.0.0.1", port=up)
        # _rae("dwl")

        # download fast
        file_data = cmd_dwf(p, int(size), ip="127.0.0.1", port=up)
        _rae("dwf")
        dl_t = time.perf_counter() - dl_t
        speed = (size / dl_t) / 1000
        lg.a('download speed {:.2f} kB/s'.format(speed))

        # save file in our local disk
        del_name = name
        if dds_get_cfg_flag_download_test_mode():
            name = TESTMODE_FILENAMEPREFIX + name
        path = str(get_dl_folder_path_from_mac(mac) / name)
        with open(path, "wb") as f:
            f.write(file_data)
        lg.a(f"downloaded file {name}")

        # calculate crc
        # path = "/tmp/ddh_crc_file"
        # with open(path, "wb") as f:
        #     f.write(file_data)
        # r_crc = cmd_crc(p, name)
        # _rae("crc")
        # # r_crc: b'CRC 08ea96f561'
        # r_crc = r_crc.decode()[-8:]
        # rv, l_crc = ble_mat_crc_local_vs_remote(path, r_crc)
        # if (not rv) and os.path.exists(path):
        #     lg.a(f"error: bad CRC so removing local file {path}")
        #     os.unlink(path)
        # if l_crc != r_crc:
        #     e = f'error: remote crc {r_crc} != local {l_crc}'
        #     lg.a(e)
        #     _rae(e)

        # add to the output list
        notes['dl_files'].append(path)

        # deleting MAT.cfg -> firmware complains
        if name == MC_FILE:
            continue

        # delete file in logger
        cmd_del(p, del_name)
        _rae("del")
        lg.a(f"deleted file {del_name}")

        # create LEF file with download info
        lg.a(f"creating file LEF for {name}")
        lef_create_file(g, name)

        # create CST file when fixed mode
        _gear_type = ddh_get_cfg_gear_type()
        if _gear_type == 0:
            gpq_create_fixed_mode_file(g, name)

    # format file-system
    time.sleep(.1)
    cmd_frm(p)
    _rae("frm")
    lg.a("FRM | OK")

    # restore the logger config file
    path = str(get_dl_folder_path_from_mac(mac) / MC_FILE)
    with open(path) as f:
        j = json.load(f)
        cmd_cfg(p, j)
        _rae("cfg")
        lg.a("CFG | OK")

    # see if the DOX sensor works
    for i_do in range(3):
        rv = cmd_gdo(p)
        if rv:
            # good!
            lg.a(f"GDO | {rv}")
            break
        lg.a(f"GDO | error {rv}")
        if i_do == 2:
            # notify this
            lat, lon, _, __ = g
            ln = LoggerNotification(mac, sn, 'DOX', b)
            ln.uuid_interaction = u
            notify_logger_error_sensor_oxygen(g, ln)
            _une(notes, "ox_sensor_error", ce=1)
            _rae("gdo")
        else:
            _u(STATE_DDS_BLE_DOWNLOAD_ERROR_GDO)
            _une(notes, "ox_sensor_error", ce=0)
        time.sleep(5)

    # see if this guy has GDX (better GDO) instruction
    time.sleep(1)
    rv = cmd_gdx(p)
    lg.a(f"GDX | (beta) {rv}")

    # wake mode
    do_we_rerun = not get_ddh_do_not_rerun_flag_li()
    w = "on" if do_we_rerun else "off"
    cmd_wak(p, w)
    _rae("wak")
    lg.a(f"WAK | {w} OK")

    if do_we_rerun:
        rv = cmd_rws(p, g)
        if not rv:
            _u(STATE_DDS_BLE_ERROR_RUN)
            time.sleep(5)
            _rae("rws")
        lg.a("RWS | OK")
        notes['rerun'] = True
    else:
        lg.a("warning: this logger is not set for auto-re-run")
        notes['rerun'] = False

    # -----------------------
    # bye, bye to this logger
    # -----------------------
    my_disconnect(p)
    return 0


def ble_interact_dox_lsb(mac, info, g, h, u):

    rv = 0
    notes = {}

    try:
        lg.a(f"debug: experimental interaction with {info}_LSB logger")
        rv = _dl_logger_dox_lsb(mac, g, notes, u, h)

    except Exception as ex:
        force_disconnect(mac)
        lg.a(f"error dl_dox_lsb_exception {ex}")
        rv = 1

    finally:
        return rv, notes


# ------
# test
# ------
if __name__ == "__main__":
    # we currently in 'ddh/dds'
    os.chdir('')
    _m = "D0:2E:AB:D9:29:48"
    force_disconnect(_m)
    _i = "DOX"
    _g = ("+1.111111", "-2.222222", datetime.now(), 0)
    _h = "hci0"
    _args = [_m, _i, _g, _h]
    _dl_logger_dox_lsb(*_args)
