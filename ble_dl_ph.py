import os.path
import time
from queue import Queue
from threading import Thread
from uuid import uuid4
import pandas as pd
from dds.notifications_v2 import *
from dds.state import state_ble_init_rv_notes
from lsb.cmd import *
from lsb.connect import *
from utils.ddh_config import (
    dds_get_cfg_logger_sn_from_mac
)
from utils.ddh_shared import (
    create_folder_logger_by_mac,
    get_dl_folder_path_from_mac,
    send_ddh_udp_gui as _u
)
from utils.logs import lg_dds as lg


UUID_S = '6e400001-b5a3-f393-e0a9-e50e24dcca9e'
UUID_T = '6e400003-b5a3-f393-e0a9-e50e24dcca9e'
_ph_rx = bytes()
q = Queue()
ts_next_put = time.perf_counter() + 5


# une: update notes error
def _une(notes, e, ce=0):
    notes["error"] = "error " + str(e)
    notes["crit_error"] = int(ce)


def _th_ph_data_saving_fxn(mac):
    while 1:
        bb = q.get()
        bs = bb.decode()
        if 'quit' in bs:
            break
        if 'Timestamp' in bs:
            continue
        if 'Green' in bs:
            continue
        if not (bs.startswith('20') and bs.endswith(' $')):
            continue
        # good string, remove the trailing
        v = bs.split(' $')[0]
        # grab the date up to the hour
        ts = v.split(',')[0]
        # write to file
        dl_fol = get_dl_folder_path_from_mac(mac)
        file_path = f'{dl_fol}/{ts[:4]}{ts[5:7]}{ts[8:10]}{ts[11:13]}_pH.csv'
        if not os.path.exists(file_path):
            print(f'creating file {file_path}')
            f = open(file_path, 'w')
            f.write('Timestamp, Dark, Blue, Green, Absorbance Blue, Absorbance Green, '
                    'R Ratio, System_Temperature, Inline_Water_Temperature, Salinity, pH, '
                    'Ref Dark, Ref Blue, Ref Green, Ref Absorbance Blue, Ref Absorbance Green\n'
                    ''.replace(', ', ','))
            f.close()
        with open(file_path, 'a') as f:
            v = v.replace(', ', ',')
            # todo ---> fix Gautam bug date
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            v = str(now) + v[19:]
            f.write(v + '\n')
    print('thread killed')


def _cb_rx_noti_ph(data):
    q.put(data)


def _dl_logger_ph_lsb(mac, g, notes: dict, u):

    state_ble_init_rv_notes(notes)
    create_folder_logger_by_mac(mac)

    # todo ---> change this
    # sn = dds_get_cfg_logger_sn_from_mac(mac)
    sn = "0000001"

    # get internal / external adapters
    ads = get_adapters()
    ad_i = 0
    ad = ads[ad_i]
    lg.a(f'using LSB with antenna hci{ad_i}')

    # scan
    ad.set_callback_on_scan_found(cb_scan)
    pp = scan_for_peripherals(ad, 10000, mac)
    found, p_i = is_mac_in_found_peripherals(pp, mac)
    if not found:
        _une(notes, "scan")
        raise Exception("error: ph scanning")

    # connect
    p = pp[p_i]
    if not connect_mac(p, mac):
        _une(notes, "comm.")
        raise Exception("error: ph connecting")
    lg.a(f"connected to {mac}")

    # configure notification
    p.notify(UUID_S, UUID_T, _cb_rx_noti_ph)

    # tell GUI we are connected
    # todo ---> do this
    # _u(f"{STATE_DDS_BLE_LOW_BATTERY}/{mac}")

    # collect pH measurements
    time.sleep(30)

    # ---------------------
    # bye, bye to pH logger
    # ---------------------
    my_disconnect(p)
    return 0


def ble_interact_ph_lsb(mac, info, g, u):

    th = Thread(target=_th_ph_data_saving_fxn, args=(mac, ))
    th.start()

    rv = 0
    notes = {}

    try:
        lg.a(f"debug: experimental interaction with {info}_LSB logger")
        rv = _dl_logger_ph_lsb(mac, g, notes, u)
        # end the data saving thread
        q.put(b'quit')

    except Exception as ex:
        force_disconnect(mac)
        lg.a(f"error dl_ph_lsb_exception {ex}")
        rv = 1

    finally:
        return rv, notes


if __name__ == "__main__":
    _m = "F9:7B:79:EF:9D:99"
    force_disconnect(_m)
    _i = "ECLIPSE_pH"
    _g = ("+1.111111", "-2.222222", datetime.now(), 0)
    _u = uuid4()
    _args = [_m, _i, _g, _u]
    ble_interact_ph_lsb(*_args)

    # show what we collected
    # df = pd.read_csv('/tmp/2024112009_pH.csv')
    # print(df['pH'])
