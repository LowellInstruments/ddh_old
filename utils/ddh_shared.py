import datetime
import glob
import time
import git
import json
import os
import socket
from pathlib import Path
from git import InvalidGitRepositoryError
import subprocess as sp
from mat.ble.ble_mat_utils import DDH_GUI_UDP_PORT


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
STATE_DDS_BLE_ERROR_MOANA_PLUGIN = "state_dds_ble_error_moana_plugin"


STATE_DDS_NOTIFY_NET_VIA = "net_via"
STATE_DDS_NOTIFY_CLOUD_BUSY = "cloud_busy"
STATE_DDS_NOTIFY_CLOUD_LOGIN = "cloud_login"
STATE_DDS_NOTIFY_CLOUD_OK = "cloud_ok"
STATE_DDS_NOTIFY_CLOUD_ERR = "cloud_error"


STATE_DDS_NOTIFY_CONVERSION_ERR = "conversion_error"
STATE_DDS_NOTIFY_CONVERSION_OK = "conversion_ok"


STATE_DDS_REQUEST_PLOT = "plot_request"
STATE_DDS_NOTIFY_PLOT_RESULT_OK = "state_dds_notify_plot_result_ok"
STATE_DDS_NOTIFY_PLOT_RESULT_ERR = "state_dds_notify_plot_result_err"


STATE_DDS_SOFTWARE_UPDATED = "software_updated"
STATE_DDS_GPS_POWER_CYCLE = "gps_power_cycle"


NAME_EXE_DDH = "main_ddh"
NAME_EXE_DDS = "main_dds"
PID_FILE_DDH = "/tmp/{}.pid".format(NAME_EXE_DDH)
PID_FILE_DDS = "/tmp/{}.pid".format(NAME_EXE_DDS)
NAME_EXE_DDH_CONTROLLER = NAME_EXE_DDH + "_controller"
NAME_EXE_DDS_CONTROLLER = NAME_EXE_DDS + "_controller"
PID_FILE_DDH_CONTROLLER = "/tmp/{}.pid".format(NAME_EXE_DDH_CONTROLLER)
PID_FILE_DDS_CONTROLLER = "/tmp/{}.pid".format(NAME_EXE_DDS_CONTROLLER)


_sk = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


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
def dds_kill_by_pid_file():
    print("[ KILL ] killing father and child DDS processes")
    c = "pkill -F {}".format(PID_FILE_DDS)
    sp.run(c, shell=True)
    c = "pkill -F {}".format(PID_FILE_DDS_CONTROLLER)
    sp.run(c, shell=True)


def ddh_get_folder_path_root() -> Path:
    return Path("ddh")


def dds_ensure_proper_working_folder():
    if not os.path.exists("main_dds.py"):
        print("{} = BAD working directory".format(os.getcwd()))
        os.exit(1)


def ddh_get_folder_path_res() -> Path:
    return Path("ddh/gui/res")


def ddh_get_settings_json_file() -> Path:
    return Path("settings/ddh.json")


def ddh_get_cc26x2r_recipe_json_file() -> Path:
    return Path("settings/recipe_cc26x2r.json")


def ddh_get_gui_closed_flag_file() -> Path:
    return Path("/tmp/gui_closed.flag")


def dds_get_gps_external_flag_file() -> str:
    return "/home/pi/li/.ddt_using_gps_external.flag"


def dds_get_is_emolt_box_flag_file() -> str:
    return "/home/pi/li/.ddt_this_is_emolt_box.flag"


def ddh_get_disabled_ble_flag_file() -> str:
    return "/tmp/ddh_disabled_ble_file.flag"


def ddh_get_app_override_flag_file() -> str:
    return "/tmp/ddh_app_override_file.flag"


def dds_get_ddh_got_an_update_flag_file() -> str:
    return "/tmp/ddh_got_update_file.flag"


def dds_get_aws_has_something_to_do_via_gui_flag_file() -> str:
    return "/tmp/ddh_aws_has_something_to_do_via_gui.flag"


def ddh_get_db_history_file() -> str:
    return "ddh/db/db_his.db"


def ddh_get_db_plots_file() -> str:
    return "ddh/db/db_plt.db"


def dds_check_we_have_box_env_info():
    if not os.getenv("DDH_BOX_SERIAL_NUMBER"):
        print("fatal error: we need a box serial number")
        os._exit(1)

    if not os.getenv("DDH_BOX_PROJECT_NAME"):
        print("fatal error: we need a box project name")
        os._exit(1)


def dds_check_conf_json_file():
    try:
        j = str(ddh_get_settings_json_file())
        with open(j) as f:
            cfg = json.load(f)
            del cfg["db_logger_macs"]
            del cfg["ship_name"]
            del cfg["forget_time"]
            del cfg["metrics"]
            del cfg["span_dict"]
            del cfg["units_temp"]
            del cfg["units_depth"]
            del cfg["last_haul"]
            del cfg["moving_speed"]
            del cfg["comment-1"]
            assert cfg == {}

    except KeyError as ke:
        print("ddh.json misses key {}".format(ke))
        os._exit(1)

    except AssertionError:
        print("ddh.json has unknown key")
        os._exit(1)

    except (Exception,) as ex:
        print(ex)
        os._exit(1)


def dds_get_macs_from_json_file():
    j = str(ddh_get_settings_json_file())
    try:
        with open(j) as f:
            cfg = json.load(f)
            known = cfg["db_logger_macs"].keys()
            return [x.lower() for x in known]
    except TypeError:
        print("error json_get_macs()")
        return {}


def ble_get_cc26x2_recipe_flags_from_json():
    j = str(ddh_get_cc26x2r_recipe_json_file())
    try:
        with open(j) as f:
            return json.load(f)
    except (Exception,):
        print("error json_get_cc26x2r_recipe()")
        return {}


def ble_set_cc26x2r_recipe_flags_to_file(j):
    path = str(ddh_get_cc26x2r_recipe_json_file())
    try:
        with open(path, "w") as f:
            f.write(json.dumps(j))
    except (Exception,):
        print("error json_set_cc26x2r_recipe()")


def dds_get_serial_number_of_macs_from_json_file():
    j = str(ddh_get_settings_json_file())
    try:
        with open(j) as f:
            cfg = json.load(f)
            known = cfg["db_logger_macs"].values()
            return [x.lower() for x in known]
    except TypeError:
        print("error json_get_sn()")
        return []


def dds_get_mac_from_sn_from_json_file(sn):
    j = str(ddh_get_settings_json_file())
    try:
        with open(j) as f:
            cfg = json.load(f)
            d = cfg["db_logger_macs"]
            inv = {v: k for k, v in d.items()}
            return inv[sn].lower()

    except TypeError:
        print("error json_get_sn()")
        return []


def ddh_get_json_plot_type():
    j = str(ddh_get_settings_json_file())
    with open(j) as f:
        cfg = json.load(f)
        v = cfg["last_haul"]
        assert v in (0, 1)
        return v


def ddh_get_is_last_haul():
    return ddh_get_json_plot_type()


def ddh_get_json_app_type():
    return ddh_get_json_plot_type()


def dds_get_json_vessel_name():
    j = str(ddh_get_settings_json_file())
    try:
        with open(j) as f:
            cfg = json.load(f)
            return cfg["ship_name"]
    except TypeError:
        return "Unnamed ship"


def dds_get_json_moving_speed() -> list:
    j = str(ddh_get_settings_json_file())
    try:
        with open(j) as f:
            cfg = json.load(f)
            max_n_min = list(cfg["moving_speed"].values())
            assert len(max_n_min) == 2
            assert max_n_min[0] <= max_n_min[1]
            return max_n_min
    except TypeError:
        print("error json_get_moving_speed()")


def _mac_dns_no_case(mac):
    """returns logger name from its mac, not case-sensitive"""

    j = str(ddh_get_settings_json_file())
    try:
        with open(j) as f:
            cfg = json.load(f)
            return cfg["db_logger_macs"][mac]
    except (FileNotFoundError, TypeError, KeyError):
        return None


def dds_get_json_mac_dns(mac):
    """returns non-case-sensitive logger name (known) or mac (unknown)"""

    # check for both upper() and lower() cases
    name = _mac_dns_no_case(mac.lower())
    if not name:
        name = _mac_dns_no_case(mac.upper())
    rv = name if name else mac
    return rv


def get_ddh_folder_path_dl_files() -> Path:
    return Path("dl_files")


def get_ddh_folder_path_logs() -> Path:
    # solves testing folders being created inside 'dds'
    p = os.getcwd()
    if p.endswith("/dds"):
        p = p.replace("/dds", "/..")
    return Path(p) / "logs"


def get_dds_folder_path_macs() -> Path:
    return Path("dds/macs")


def get_ddh_folder_path_macs_black() -> Path:
    return get_dds_folder_path_macs() / "black"


def get_ddh_folder_path_macs_orange() -> Path:
    return get_dds_folder_path_macs() / "orange"


def get_ddh_folder_path_sqs() -> Path:
    return Path("dds/sqs")


def get_ddh_folder_path_lef() -> Path:
    return Path("dds/lef")


def get_ddh_folder_path_rbl() -> Path:
    return Path("dds/rbl")


def get_ddh_folder_path_settings() -> Path:
    return Path("settings")


def get_ddh_loggers_forget_time() -> int:
    j = str(ddh_get_settings_json_file())
    try:
        with open(j) as f:
            cfg = json.load(f)
            return cfg["forget_time"]

    except (FileNotFoundError, TypeError, KeyError) as ex:
        e = "error get_ddh_loggers_forget_time {}"
        print(e.format(ex))
        os.exit(1)


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


def get_ddh_commit():
    try:
        _r = git.Repo(".")
        c = _r.head.commit
        return str(c)[:5]
    except InvalidGitRepositoryError:
        return "none"


def get_utc_offset():
    ts = time.time()
    utc_offset = (
        datetime.datetime.fromtimestamp(ts) - datetime.datetime.utcfromtimestamp(ts)
    ).total_seconds()
    return utc_offset


def get_dl_files_type(path):
    ls_lid = len(glob.glob('{}/*.lid'.format(path)))
    if ls_lid:
        return 'lid'
    ls_bin = len(glob.glob('{}/*.bin'.format(path)))
    if ls_bin:
        return 'bin'
    print('I dont know what files to search for')
    return ''


def main():
    print(ddh_get_folder_path_root())


if __name__ == "__main__":
    main()
