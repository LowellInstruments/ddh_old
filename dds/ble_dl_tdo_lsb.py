from dds.gpq import gpq_create_fixed_mode_file
from dds.lef import lef_create_file
from dds.notifications_v2 import *
from dds.state import state_ble_init_rv_notes, state_ble_logger_ccx26x2r_needs_a_reset
from lsb.cmd import *
from lsb.connect import *
from lsb.li import UUID_S, UUID_T
from lsb.utils import DDH_GUI_UDP_PORT
from mat.ble.ble_mat_utils import ble_mat_crc_local_vs_remote
from utils.ddh_config import (
    dds_get_cfg_logger_sn_from_mac,
    dds_get_cfg_flag_download_test_mode,
    ddh_get_cfg_gear_type, exp_get_ble_do_crc
)
from utils.ddh_shared import (
    BLEAppException, create_folder_logger_by_mac,
    get_dl_folder_path_from_mac,
    send_ddh_udp_gui as _u,
    STATE_DDS_BLE_LOW_BATTERY, TESTMODE_FILENAMEPREFIX,
    STATE_DDS_BLE_DOWNLOAD_ERROR_TP_SENSOR,
    get_ddh_do_not_rerun_flag_li, STATE_DDS_BLE_ERROR_RUN,
)
from utils.logs import lg_dds as lg


g_debug_not_delete_files = False
BAT_FACTOR_TDO = 0.5454


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
    raise BLEAppException("TDO interact LSB: " + s)


def _dl_logger_tdo_lsb(mac, g, notes: dict, u, hs):

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
        _rae("scanning")

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
        raise BLEAppException("TDO interact logger reset file")

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
    b /= BAT_FACTOR_TDO
    lg.a(f"BAT | ADC {adc_b} mV -> battery {int(b)} mV")
    notes["battery_level"] = b
    if adc_b < 982:
        ln = LoggerNotification(mac, sn, 'TDO', adc_b)
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
        if exp_get_ble_do_crc() == 1:
            path = "/tmp/ddh_crc_file"
            with open(path, "wb") as f:
                f.write(file_data)
            r_crc = cmd_crc(p, name)
            _rae("crc")
            # r_crc: b'CRC 08ea96f561'
            r_crc = r_crc.decode()[-8:]
            rv, l_crc = ble_mat_crc_local_vs_remote(path, r_crc)
            if (not rv) and os.path.exists(path):
                lg.a(f"error: bad CRC so removing local file {path}")
                os.unlink(path)
            if l_crc != r_crc:
                e = f'error: remote crc {r_crc} != local {l_crc}'
                lg.a(e)
                _rae(e)
        else:
            lg.a('warning: dl_tdo_lsb skips file CRC calculation')

        # add to the output list
        notes['dl_files'].append(path)

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

    # check sensors measurement, Temperature
    rv = cmd_gst(p)
    if not rv:
        _une(notes, "T_sensor_error")
        lg.a(f'GST | error {rv}')
        _u(STATE_DDS_BLE_DOWNLOAD_ERROR_TP_SENSOR)
        time.sleep(5)
    _rae("gst")

    # check sensors measurement, Pressure
    rv = cmd_gsp(p)
    if not rv:
        _une(notes, "P_sensor_error")
        lg.a(f'GSP | error {rv}')
        ln = LoggerNotification(mac, sn, 'TDO', b)
        ln.uuid_interaction = u
        notify_logger_error_sensor_pressure(g, ln)
        _u(STATE_DDS_BLE_DOWNLOAD_ERROR_TP_SENSOR)
        time.sleep(5)
    _rae("gsp")

    # get the rerun flag
    rerun_flag = not get_ddh_do_not_rerun_flag_li()

    # wake mode
    w = "on" if rerun_flag else "off"
    cmd_wak(p, w)
    _rae("wak")
    lg.a(f"WAK | {w} OK")

    # re-run logger, maybe
    if rerun_flag:
        rv = cmd_rws(p, g)
        if not rv:
            _u(STATE_DDS_BLE_ERROR_RUN)
            time.sleep(5)
            _rae("rws")
        lg.a("RWS | OK")
    else:
        lg.a("warning: this logger is not set for auto-re-run")
    notes['rerun'] = rerun_flag

    # -----------------------
    # bye, bye to this logger
    # -----------------------
    my_disconnect(p)
    return 0


def ble_interact_tdo_lsb(mac, info, g, h, u):

    rv = 0
    notes = {}

    try:
        lg.a(f"debug: experimental interaction with {info}_LSB logger")
        rv = _dl_logger_tdo_lsb(mac, g, notes, u, h)

    except Exception as ex:
        force_disconnect(mac)
        lg.a(f"error dl_tdo_lsb_exception {ex}")
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
    _i = "TDO"
    _g = ("+1.111111", "-2.222222", datetime.now(), 0)
    _h = "hci0"
    _args = [_m, _i, _g, _h]
    ble_interact_tdo_lsb(*_args)
