import datetime
import json
from dds.gps_ctt import *
from dds.notifications_v2 import notify_ddh_error_hw_gps
from dds.timecache import is_it_time_to
from mat.quectel import FILE_QUECTEL_USB_CTL, FILE_QUECTEL_USB_GPS
from mat.utils import linux_is_rpi, linux_set_datetime
from tzlocal import get_localzone

from utils.flag_paths import (
    TMP_PATH_DDH_BOAT_SPEED_JSON,
)
from utils.ddh_config import (dds_get_cfg_vessel_name,
                              )
from utils.ddh_shared import (
    send_ddh_udp_gui as _u,
    STATE_DDS_NOTIFY_BOAT_NAME,
    STATE_DDS_NOTIFY_GPS_CLOCK,
    check_gps_dummy_mode,
)
from utils.logs import lg_gps as lg
from utils.find_usb_port_auto import find_usb_port_automatically


# global variables
_g_ever_gps_clock_sync = False


def gps_utils_bu353s4_find_usb_port():
    # the GPS USB puck has 2 PIDs
    p = find_usb_port_automatically('067B:2303')
    if p:
        return p
    # try the other one
    return find_usb_port_automatically('067B:23A3')


def gps_utils_clock_sync_if_so(dt_gps_utc) -> bool:
    """
    returning True means GPS time synchronized
    """

    global _g_ever_gps_clock_sync

    if not linux_is_rpi():
        # we don't do it when developing
        _g_ever_gps_clock_sync = True
        return True

    if not dt_gps_utc:
        return False

    if type(dt_gps_utc) is not datetime.datetime:
        lg.a("bad type to sync time via GPS")
        return False

    # use GPS time in parameter to sync local clock
    utc_now = datetime.datetime.utcnow()
    diff_secs = abs((dt_gps_utc - utc_now).total_seconds())
    if diff_secs < 60:
        _g_ever_gps_clock_sync = True
        return True
    lg.a(f"debug: gps_cloc_sync_diff_secs = {diff_secs}")
    z_my = get_localzone()
    z_utc = datetime.timezone.utc
    dt_my = dt_gps_utc.replace(tzinfo=z_utc).astimezone(tz=z_my)
    t = str(dt_my)[:-6]

    # this is a bool
    if linux_set_datetime(t):
        _g_ever_gps_clock_sync = True
        return True
    return False


def gps_utils_tell_vessel_name():
    if not is_it_time_to("tell_vessel_name", PERIOD_GPS_TELL_VESSEL_SECS):
        return
    v = dds_get_cfg_vessel_name()
    _u(f"{STATE_DDS_NOTIFY_BOAT_NAME}/{v}")


def gps_utils_tell_position_logger(g):
    lat, lon, tg, speed = g
    lg.a(f"starting logger processing at {lat}, {lon}, speed {speed}")


def gps_utils_check_for_errors(g) -> int:
    if g:
        # no error
        return 0

    # don't log GPS error too often
    if is_it_time_to("tell_gps_hw_error", PERIOD_GPS_TELL_GPS_HW_ERROR_SECS):
        lg.a("error: no GPS frame, examine further log messages")
        notify_ddh_error_hw_gps()

    # detect errors in GPS frame
    if not g:
        lg.a("error: no GPS frame, will not interact w/ loggers")
        return 1
    lat, lon, tg, speed = g
    if not lat:
        lg.a("error: no GPS latitude, will not interact w/ loggers")
        return 1
    lg.a(f"error: GPS unexpected {g}")
    return 1


def gps_utils_banner_clock_sync_at_boot():
    if not check_gps_dummy_mode():
        lg.a("trying clock sync via GPS at boot")
        return
    lg.a("warning: dummy GPS, not syncing clock via GPS at boot")


def gps_utils_did_we_ever_clock_sync() -> bool:
    _u(STATE_DDS_NOTIFY_GPS_CLOCK)
    return _g_ever_gps_clock_sync


def gps_simulate_boat_speed(s_lo, knots, s_hi):
    try:
        with open(TMP_PATH_DDH_BOAT_SPEED_JSON, "r") as f:
            # file content
            # {
            #     "knots_min": 3,
            #     "knots_max": 5,
            #     "knots_set": 4
            # }
            j = json.load(f)
            k_min = j['knots_min']
            k_max = j['knots_max']
            k_set = j['knots_set']
            lg.a("warning: using simulated boat speeds")
            lg.a(f"set {k_set} min {k_min} max {k_max}")
            return float(k_min), float(k_set), float(k_max)

    except (Exception, ):
        return s_lo, knots, s_hi


def gps_get_quectel_usb_port_from_file(s):
    assert s in ('gps', 'ctl')
    if s == 'gps':
        try:
            with open(FILE_QUECTEL_USB_GPS) as f:
                return f.readline()
        except (Exception, ) as ex:
            print(f'error: gps_get_port_from_file for {s} -> {ex}')

    if s == 'ctl':
        try:
            with open(FILE_QUECTEL_USB_CTL) as f:
                return f.readline()
        except (Exception, ) as ex:
            print(f'error: gps_get_port_from_file for {s} -> {ex}')
