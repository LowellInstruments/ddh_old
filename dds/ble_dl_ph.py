import os.path
import threading
import uuid
from queue import Queue
from uuid import uuid4
from dds.notifications_v2 import *
from dds.state import state_ble_init_rv_notes
from lsb.cmd import *
from lsb.connect import *
from utils.ddh_config import (
    dds_get_cfg_monitored_pairs
)
from utils.ddh_shared import (
    create_folder_logger_by_mac,
    get_dl_folder_path_from_mac,
    send_ddh_udp_gui as _u,
    STATE_DDS_BLE_CONNECTING,
    STATE_DDS_BLE_PH_CONNECTED,
    STATE_DDS_BLE_DOWNLOAD, STATE_DDS_BLE_DOWNLOAD_STATISTICS
)
from utils.logs import lg_dds as lg


UUID_S = '6e400001-b5a3-f393-e0a9-e50e24dcca9e'
UUID_T = '6e400003-b5a3-f393-e0a9-e50e24dcca9e'
_ph_rx = bytes()
q = Queue()
TIME_LENGTH_PH_DL_SECS = 60


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

        # grab the date
        # todo: choose this or grab logger first column
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

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
            v = ts + v[19:]
            f.write(v + '\n')

            # send to GUI
            day = v.split(',')[0].split(' ')[0]
            secs = v.split(',')[0].split(' ')[1]
            v_wt = v.split(',')[8]
            v_ph = v.split(',')[10]
            s = f'{day}\n{secs}\nT = {v_wt}\npH = {v_ph}\n'
            _u(f"{STATE_DDS_BLE_DOWNLOAD_STATISTICS}/{s}")
    print('thread killed')


def _cb_rx_noti_ph(data):
    # towards data saving thread
    q.put(data)


def _dl_logger_ph_lsb(g):

    d = dds_get_cfg_monitored_pairs()
    found_ph = False
    found_mac = ''
    found_sn = ''
    for mac, sn in d.items():
        if sn.startswith('9'):
            found_ph = True
            found_mac = mac
            found_sn = sn
            break

    if not found_ph:
        return 0

    lg.a(f"debug: experimental interaction with ph_LSB logger")
    _u(f"{STATE_DDS_BLE_DOWNLOAD_STATISTICS}/' '")
    mac = found_mac
    sn = found_sn
    notes = {}
    state_ble_init_rv_notes(notes)
    create_folder_logger_by_mac(mac)
    uuid_interaction = str(uuid.uuid4())
    notes['uuid_interaction'] = uuid_interaction
    notes['gps'] = g

    _u(f"{STATE_DDS_BLE_DOWNLOAD}/{sn}")
    lg.a(f"processing pH logger {sn} / mac {mac}")

    # get internal / external adapters
    ads = get_adapters()
    ad_i = 0
    ad = ads[ad_i]
    lg.a(f'using LSB with antenna hci{ad_i}')

    # update GUI with connection icon
    _u(f"{STATE_DDS_BLE_CONNECTING}/{sn}")

    # scan
    ad.set_callback_on_scan_found(cb_scan)
    pp = scan_for_peripherals(ad, 10000, mac)
    found, p_i = is_mac_in_found_peripherals(pp, mac)
    if not found:
        _une(notes, "scan")
        raise Exception("error: pH scanning")

    # connect
    p = pp[p_i]
    if not connect_mac(p, mac):
        _une(notes, "comm.")
        raise Exception("error: pH connecting")
    lg.a(f"connected to {mac}")

    # start separate data saving thread
    lg.a(f'downloading pH logger {sn} for {TIME_LENGTH_PH_DL_SECS} seconds')
    th = threading.Thread(
        target=_th_ph_data_saving_fxn,
        args=(mac, ))
    th.start()

    # configure notification
    p.notify(UUID_S, UUID_T, _cb_rx_noti_ph)

    # collect pH measurements
    for j in range(TIME_LENGTH_PH_DL_SECS):
        time.sleep(1)
        _u(f"{STATE_DDS_BLE_PH_CONNECTED}/{sn}")

    # ---------------------
    # bye, bye to pH logger
    # ---------------------
    my_disconnect(p)
    return 0


def ble_interact_ph_lsb(g):

    rv = 0

    try:
        # we operate for a certain amount of time
        rv = _dl_logger_ph_lsb(g)
        # end the data saving thread
        q.put(b'quit')
    except Exception as ex:
        lg.a(f"error dl_ph_lsb_exception {ex}")
        rv = 1
        force_disconnect()

    finally:
        # todo: do this
        #  STATE_DDS_NOTIFY_HISTORY
        # todo: do this
        # notify_logger_download_or_error
        return rv


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
