import asyncio
import datetime
import glob
import pathlib
import time
import git
import os
import socket
from pathlib import Path
from git import InvalidGitRepositoryError
import subprocess as sp
from mat.utils import linux_is_rpi, linux_is_rpi3, linux_is_rpi4
import toml


STATE_DDS_NOTIFY_BOAT_NAME = "boat_name"
STATE_DDS_NOTIFY_GPS = "gps"
STATE_DDS_NOTIFY_GPS_CLOCK = "gps_clock_time_sync"
STATE_DDS_NOTIFY_GPS_NUM_SAT = "gps_num_sat"
STATE_DDS_NOTIFY_GPS_BOOT = "gps_boot"
STATE_DDS_NOTIFY_HISTORY = "history"


STATE_DDS_BLE_SCAN = "state_dds_ble_scan"
STATE_DDS_BLE_SCAN_FIRST_EVER = "state_dds_ble_scan_first_ever"
STATE_DDS_BLE_DOWNLOAD = "state_dds_ble_download"
STATE_DDS_BLE_DOWNLOAD_OK = "state_dds_ble_download_ok"
STATE_DDS_BLE_DOWNLOAD_ERROR = "state_dds_ble_download_error"
STATE_DDS_BLE_DOWNLOAD_ERROR_GDO = "state_dds_ble_download_error_gdo"
STATE_DDS_BLE_DOWNLOAD_ERROR_TP_SENSOR = "state_dds_ble_download_error_tp_sensor"
STATE_DDS_BLE_DOWNLOAD_WARNING = "state_dds_ble_download_warning"
STATE_DDS_BLE_DOWNLOAD_PROGRESS = "state_dds_ble_download_progress"
STATE_DDS_BLE_HARDWARE_ERROR = "state_dds_ble_hardware_error"
STATE_DDS_BLE_DISABLED = "state_dds_ble_disabled"
STATE_DDS_BLE_APP_GPS_ERROR_POSITION = "state_dds_ble_gps_error_position"
STATE_DDS_BLE_APP_GPS_ERROR_SPEED = "state_dds_ble_gps_error_speed"
STATE_DDS_BLE_SERVICE_INACTIVE = "state_dds_ble_service_inactive"
STATE_DDS_BLE_ANTENNA = "state_dds_ble_antenna_is"
STATE_DDS_BLE_LOW_BATTERY = "state_dds_ble_low_battery"
STATE_DDS_BLE_RUN_STATUS = "state_dds_ble_run_status"
STATE_DDS_BLE_NO_ASSIGNED_LOGGERS = "state_dds_ble_no_assigned_loggers"
STATE_DDS_BLE_ERROR_MOANA_PLUGIN = "state_dds_ble_error_moana_plugin"
STATE_DDS_BLE_ERROR_RUN = "state_dds_ble_error_run"


STATE_DDS_NOTIFY_NET_VIA = "net_via"
STATE_DDS_NOTIFY_CLOUD_BUSY = "cloud_busy"
STATE_DDS_NOTIFY_CLOUD_LOGIN = "cloud_login"
STATE_DDS_NOTIFY_CLOUD_OK = "cloud_ok"
STATE_DDS_NOTIFY_CLOUD_ERR = "cloud_error"


STATE_DDS_NOTIFY_CONVERSION_ERR = "conversion_error"
STATE_DDS_NOTIFY_CONVERSION_OK = "conversion_ok"


STATE_DDS_REQUEST_GRAPH = "graph_request"


STATE_DDS_SOFTWARE_UPDATED = "software_updated"
STATE_DDS_GPS_POWER_CYCLE = "gps_power_cycle"


NAME_EXE_DDH = "main_ddh"
NAME_EXE_DDS = "main_dds"
NAME_EXE_API = "main_api"
PID_FILE_DDH = "/tmp/{}.pid".format(NAME_EXE_DDH)
PID_FILE_DDS = "/tmp/{}.pid".format(NAME_EXE_DDS)
PID_FILE_API = "/tmp/{}.pid".format(NAME_EXE_API)
NAME_EXE_DDH_CONTROLLER = NAME_EXE_DDH + "_controller"
NAME_EXE_DDS_CONTROLLER = NAME_EXE_DDS + "_controller"
PID_FILE_DDH_CONTROLLER = "/tmp/{}.pid".format(NAME_EXE_DDH_CONTROLLER)
PID_FILE_DDS_CONTROLLER = "/tmp/{}.pid".format(NAME_EXE_DDS_CONTROLLER)


_sk = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


# for asynchronous Bleak BLE
ael = asyncio.get_event_loop()


class BLEAppException(Exception):
    pass


# post must match the one in MAT library
DDH_GUI_UDP_PORT = 12349


def send_ddh_udp_gui(s, ip="127.0.0.1", port=DDH_GUI_UDP_PORT):
    if "/" not in s:
        s += "/"

    _sk.sendto(s.encode(), (ip, port))
    if ip == "127.0.0.1":
        # only once on local cases
        return

    # on remote cases, both local and remote
    _sk.sendto(s.encode(), (ip, port))


# used by GUI on upper-X, 'q', clicking uptime and ctrl+c
def dds_kill_by_pid_file(only_child=False):
    print("[ KILL ] killing DDS child process")
    c = "pkill -F {}".format(PID_FILE_DDS)
    sp.run(c, shell=True)
    if only_child:
        return
    print("[ KILL ] killing DDS controller process")
    c = "pkill -F {}".format(PID_FILE_DDS_CONTROLLER)
    sp.run(c, shell=True)


def ddh_kill_by_pid_file(only_child=False):
    if not only_child:
        print("[ KILL ] killing DDH controller process")
        c = "pkill -F {}".format(PID_FILE_DDH_CONTROLLER)
        sp.run(c, shell=True)
    print("[ KILL ] killing DDH child process")
    c = "pkill -F {}".format(PID_FILE_DDH)
    sp.run(c, shell=True)


def dds_ensure_proper_working_folder():
    if not os.path.exists("main_dds.py"):
        print("{} = BAD working directory".format(os.getcwd()))
        os.exit(1)


def ddh_get_folder_path_res() -> Path:
    p = str(ddh_get_root_folder_path())
    return Path(f"{p}/ddh/gui/res")


def ddh_get_gui_closed_flag_file() -> Path:
    return Path("/tmp/gui_closed.flag")


def dds_get_is_emolt_box_flag_file() -> str:
    return "/home/pi/li/.ddt_this_is_emolt_box.flag"


def ddh_get_disabled_ble_flag_file() -> str:
    return "/tmp/ddh_disabled_ble_file.flag"


def ddh_get_app_override_flag_file() -> str:
    # set this with the clear-lockout physical button
    # to force at least one execution even with
    # boat not moving on haul mode
    return "/tmp/ddh_app_override_file.flag"


def dds_get_ddh_got_an_update_flag_file() -> str:
    return "/tmp/ddh_got_update_file.flag"


def dds_get_aws_has_something_to_do_via_gui_flag_file() -> str:
    return "/tmp/ddh_aws_has_something_to_do_via_gui.flag"


def ddh_get_db_history_file() -> str:
    p = str(ddh_get_root_folder_path())
    return f"{p}/ddh/db/db_his.json"


def get_ddh_commit():
    try:
        _r = git.Repo(".")
        c = _r.head.commit
        return str(c)[:5]
    except InvalidGitRepositoryError:
        return "none"


def get_ddh_sw_version():
    path = str(ddh_get_root_folder_path()) + '/.ddh_version'
    try:
        with open(path, 'r') as f:
            return f.readline().replace('\n', '')
    except (Exception, ) as ex:
        return 'error_get_version'


def get_ddh_folder_path_dl_files() -> Path:
    p = str(ddh_get_root_folder_path())
    return Path(f"{p}/dl_files")


def get_ddh_folder_path_logs() -> Path:
    # solves testing folders being created inside 'dds'
    p = os.getcwd()
    if p.endswith("/dds"):
        p = p.replace("/dds", "/..")
    return Path(p) / "logs"


def get_dds_folder_path_macs() -> Path:
    p = str(ddh_get_root_folder_path())
    return Path(f"{p}/dds/macs")


def get_ddh_folder_path_macs_black() -> Path:
    return get_dds_folder_path_macs() / "black"


def get_ddh_folder_path_macs_orange() -> Path:
    return get_dds_folder_path_macs() / "orange"


def get_ddh_folder_path_sqs() -> Path:
    p = str(ddh_get_root_folder_path())
    return Path(f"{p}/dds/sqs")


def get_ddh_folder_path_lef() -> Path:
    p = str(ddh_get_root_folder_path())
    return Path(f"{p}/dds/lef")


def get_ddh_folder_path_rbl() -> Path:
    p = str(ddh_get_root_folder_path())
    return Path(f"{p}/dds/rbl")


def get_ddh_folder_path_settings() -> Path:
    p = str(ddh_get_root_folder_path())
    return Path(f"{p}/settings")


def get_ddh_folder_path_tweak() -> Path:
    p = str(ddh_get_root_folder_path())
    return Path(f"{p}/dds/tweak")


def get_mac_from_folder_path(fol):
    """returns '11:22:33' from 'dl_files/11-22-33'"""
    try:
        return fol.split("/")[-1].replace("-", ":")
    except (ValueError, Exception):
        return None


def get_dl_folder_path_from_mac(mac):
    """returns 'dl_files/11-22-33' from '11:22:33'"""
    fol = get_ddh_folder_path_dl_files()
    fol = fol / "{}/".format(mac.replace(":", "-").lower())
    return fol


def create_folder_logger_by_mac(mac):
    """mkdir folder based on mac, replaces ':' with '-'"""
    fol = get_ddh_folder_path_dl_files()
    fol = fol / "{}/".format(mac.replace(":", "-").lower())
    os.makedirs(fol, exist_ok=True)
    return fol


def dds_create_folder_dl_files():
    r = get_ddh_folder_path_dl_files()
    os.makedirs(r, exist_ok=True)


def dds_create_folder_logs():
    r = get_ddh_folder_path_logs()
    os.makedirs(r, exist_ok=True)


def get_utc_offset():
    ts = time.time()
    utc_offset = (
        datetime.datetime.fromtimestamp(ts) - datetime.datetime.utcfromtimestamp(ts)
    ).total_seconds()
    return utc_offset


def get_number_of_hauls(path):
    # path: /home/kaz/PycharmProjects/ddh/dl_files/<mac>
    ls_lid = len(glob.glob('{}/*.lid'.format(path)))
    ls_lix = len(glob.glob('{}/*.lix'.format(path)))
    ls_bin = (len(glob.glob('{}/moana*.bin'.format(path))) +
              len(glob.glob('{}/MOANA*.bin'.format(path))))
    mask = '__what__'
    if ls_lid:
        # for DO & TP loggers
        mask_do = f'{path}/*_DissolvedOxygen.csv'
        mask_tp = f'{path}/*_Pressure.csv'
        n_do = len(glob.glob(mask_do))
        n_tp = len(glob.glob(mask_tp))
        mask = mask_do if n_do else mask_tp
    elif ls_lix:
        # todo ---> check this
        mask = f'{path}/*.lix'
    elif ls_bin:
        # NOT MOANA*.csv but Lowell generated files
        mask = f'{path}/*_Pressure.csv'

    n = len(glob.glob(mask))
    return n


def ddh_get_root_folder_path() -> Path:
    p = pathlib.Path.home()
    if linux_is_rpi():
        p = str(p) + '/li/ddh'
    else:
        p = str(p) + '/PycharmProjects/ddh'
    return Path(p)


def ddh_get_root_folder_path_as_str():
    return str(ddh_get_root_folder_path())


GPS_DUMMY_MODE_FILE = '/tmp/gps_dummy_mode.json'


def check_gps_dummy_mode():
    if not linux_is_rpi():
        return True
    return os.path.exists(GPS_DUMMY_MODE_FILE)


def get_ddh_platform():
    if linux_is_rpi3():
        return "rpi3"
    elif linux_is_rpi4():
        return "rpi4"
    elif linux_is_rpi():
        return "rpi"
    return "unk"


def get_ddh_toml_all_macs_content():
    p = str(ddh_get_root_folder_path())
    p = f"{p}/settings/all_macs.toml"

    try:
        with open(p, 'r') as f:
            # d: {'11:22:33:44:55:66': 'sn1234567'}
            return toml.load(f)
    except (Exception,) as ex:
        print('error: get_ddh_toml_all_macs_content: ', ex)
        os._exit(1)


def set_ddh_toml_all_macs_content(d):
    p = str(ddh_get_root_folder_path())
    p = f"{p}/settings/all_macs.toml"

    try:
        with open(p, 'w') as f:
            # d: {'11:22:33:44:55:66': 'sn1234567'}
            toml.dump(d, f)
            print(d)
    except (Exception,) as ex:
        print('error: get_ddh_toml_all_macs_content: ', ex)
        os._exit(1)


def get_ddh_rerun_flag_li():
    p = str(ddh_get_root_folder_path())
    f = f'{p}/settings/rerun_flag.toml'
    return os.path.exists(f)


def set_ddh_rerun_flag_li():
    p = str(ddh_get_root_folder_path())
    f = f'{p}/settings/rerun_flag.toml'
    pathlib.Path(f).touch()


def clr_ddh_rerun_flag_li():
    p = str(ddh_get_root_folder_path())
    f = f'{p}/settings/rerun_flag.toml'
    try:
        os.unlink(f)
    except (Exception, ) as ex:
        print(f'error clr_ddh_rerun_flag_li -> {ex}')


def main():
    get_ddh_toml_all_macs_content()


if __name__ == "__main__":
    main()
