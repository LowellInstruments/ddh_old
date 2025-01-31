import datetime
import json
import re
import time
import serial
from gpiozero import LED
from dds.gps_ctt import *
from dds.gps_utils import (
    gps_utils_bu353s4_find_usb_port,
    gps_get_quectel_usb_port_from_file
)
from dds.notifications_v2 import (
    notify_ddh_number_of_gps_satellites,
    notify_ddh_error_hw_gps
)
from dds.timecache import is_it_time_to
from mat.quectel import (
    is_this_telit_cell,
    detect_quectel_usb_ports
)
from utils.ddh_config import (
    dds_get_cfg_flag_gps_error_forced,
    dds_get_cfg_fake_gps_position,
    dds_get_cfg_flag_gps_external
)
from utils.ddh_shared import (
    send_ddh_udp_gui as _u,
    STATE_DDS_GPS_POWER_CYCLE,
    check_gps_dummy_mode,
    STATE_DDS_BLE_APP_GPS_ERROR_POSITION,
    STATE_DDS_NOTIFY_GPS,
    STATE_DDS_NOTIFY_GPS_NUM_SAT,
    STATE_DDS_NOTIFY_GPS_BOOT,
)
from utils.flag_paths import (
    TMP_PATH_GPS_LAST_JSON,
    LI_PATH_CELL_FW
)
from utils.logs import lg_gps as lg


class myGpsException(Exception):
    pass


_g_ts_cached_gps_valid_for = 0
_g_cached_gps = None
_g_banner_cache_too_old = 0


# pu_gps: port USB gps for Quectel shields
_g_pu_gps = gps_get_quectel_usb_port_from_file('gps')
_g_pu_ctl = gps_get_quectel_usb_port_from_file('ctl')
if not _g_pu_gps and not _g_pu_ctl:
    if not is_this_telit_cell():
        _g_pu_gps, _g_pu_ctl = detect_quectel_usb_ports()
# fallback
if not _g_pu_gps:
    _g_pu_gps = '/dev/ttyUSB1'
if not _g_pu_ctl:
    _g_pu_ctl = '/dev/ttyUSB2'

# for external GPS puck config
_g_bu353s4_port = None
if dds_get_cfg_flag_gps_external():
    _g_bu353s4_port = gps_utils_bu353s4_find_usb_port()

# global variable for GPS serial port whatever its shape is
_g_sp = None


def gps_know_hat_firmware_version():

    if check_gps_dummy_mode():
        return

    if _g_bu353s4_port:
        return

    _sp = None
    try:
        _sp = serial.Serial(
            _g_pu_ctl, baudrate=115200,
            timeout=1, rtscts=True, dsrdtr=True
        )
        _sp.flushInput()
        _sp.readall()
        _sp.write(b"AT+CVERSION\r")
        ans_v = _sp.readall()
        _sp.write(b"AT+QGMR\r")
        ans_m = _sp.readall()
        ans_v = ans_v.replace(b"OK", b"")
        ans_v = ans_v.replace(b"\r\n", b"")
        ans_m = ans_m.replace(b"OK", b"")
        ans_m = ans_m.replace(b"\r\n", b"")
        if ans_v:
            lg.a(f"debug: firmware CVERSION {ans_v}")
            with open(LI_PATH_CELL_FW, 'w') as f:
                f.write(ans_v.decode())
        else:
            lg.a("error: firmware CVERSION")
        if ans_m:
            lg.a(f"debug: firmware GMR {ans_m}")
        else:
            lg.a("error: firmware GMR")

    except (Exception,) as ex:
        lg.a(f"error: hat_firmware_version -> {ex}")

    finally:
        if _sp:
            _sp.close()

    time.sleep(0.1)


def _open_gps():
    global _g_sp
    if _g_bu353s4_port:
        _g_sp = serial.Serial(_g_bu353s4_port, 4800, timeout=0.2)
    else:
        _g_sp = serial.Serial(_g_pu_gps, baudrate=115200, timeout=0.2,
                              rtscts=True, dsrdtr=True)


def _close_gps():
    global _g_sp
    if _g_sp and _g_sp.is_open:
        _g_sp.close()


def _activate_gps_output():
    _open_gps()
    b = bytes()
    till = time.perf_counter() + 1
    _g_sp.write(b'AT+QGPS=1 \rAT+QGPS=1 \r')
    while time.perf_counter() < till:
        try:
            b += _g_sp.read()
        except (Exception,) as ex:
            lg.a(f'error: _activate_gps_output: -> {ex}')
    _close_gps()
    if (b'GPGSV' in b or b'GPGSA' in b
            or b'GPRMC' in b or b',,,,' in b
            or b'\x00\x00\x00' in b):
        return True


def _gps_coord_decode(coord: str):
    # src: stackoverflow 18442158 latitude format
    x = coord.split(".")
    head = x[0]
    deg = head[:-2]
    minutes = f"{head[-2:]}.{x[1]}"
    decimal = int(deg) + float(minutes) / 60
    return decimal


def _gps_parse_rmc_frame(data: bytes):
    """
    parse fields in an RMC NMEA string
    """

    if b"GPRMC" not in data:
        return

    data = data.decode()
    s = "$GPRMC" + data.split("$GPRMC")[1].split("\r")[0]
    s = s.split(",")
    if s[2] == "V":
        return

    _t = s[1][0:2] + ":" + s[1][2:4] + ":" + s[1][4:6]
    _day = s[9][0:2] + "/" + s[9][2:4] + "/" + s[9][4:6]

    # lat, direction, lon, direction, speed, course, variation
    lat = _gps_coord_decode(s[3])
    dir_lat = s[4]
    lon = _gps_coord_decode(s[5])
    dir_lon = s[6]
    speed = s[7]
    _course = s[8]
    # variation = s[10]

    # GPS date and time are UTC
    fmt = f"{_day} {_t}"
    gps_time = datetime.datetime.strptime(fmt, "%d/%m/%y %H:%M:%S")

    # return some strings
    lat = lat * 1 if dir_lat == "N" else lat * -1
    lon = lon * 1 if dir_lon == "E" else lon * -1

    # checksum skipping initial '$'
    cs_in = data.split("*")[1][:2]
    cs_calc = 0
    for c in data[1:].split("*")[0]:
        cs_calc ^= ord(c)
    cs_calc = "{:02x}".format(int(cs_calc))
    if cs_in != cs_calc.upper():
        return None

    # save to disk for other apps such as DDH API
    try:
        d = {
           "lat": "{:.4f}".format(lat),
           "lon": "{:.4f}".format(lon),
           "gps_time": str(gps_time),
           "speed": speed
        }
        with open(TMP_PATH_GPS_LAST_JSON, "w") as f:
            json.dump(d, f)
    except (Exception, ) as ex:
        lg.a(f'error: saving {TMP_PATH_GPS_LAST_JSON} -> {ex}')

    # everything went OK
    return lat, lon, gps_time, speed


def _gps_parse_gsv_frame(data: bytes, force_print=False):
    """
    parse fields in a GSV NMEA string
    """

    # data: b'$GPGSV,...,$GPGGA,...' all mixed
    if b"GPGSV" not in data:
        return -1

    # $GPGSV, #messages, msg_num, num sat, ...
    data = data.decode()
    data = data.split(",")
    idx = data.index("$GPGSV")
    data = data[idx:]

    # log satellites but not always
    try:
        n = int(data[3])
        if force_print or is_it_time_to("show_gsv_frame",
                                        PERIOD_GPS_TELL_NUM_SATS_SECS):
            _u(f"{STATE_DDS_NOTIFY_GPS_NUM_SAT}/{n}")
            if n < 7:
                lg.a(f"{n} satellites in view")
        return n

    except (Exception,) as ex:
        lg.a(f"error: parse GSV frame {data} -> {ex}")
        return -1


def gps_utils_boot_wait_long():

    # Wikipedia: GPS-Time-To-First-Fix for cold start is typ.
    # 2 to 5 minutes, warm <= 45 secs, hot <= 22 secs

    t_till = int(time.perf_counter() + PERIOD_GPS_AT_BOOT_SECS)
    lg.a(f"boot: wait up to {PERIOD_GPS_AT_BOOT_SECS} seconds")

    while time.perf_counter() < t_till:
        t_left = int(t_till - time.perf_counter())
        _u(f"{STATE_DDS_NOTIFY_GPS_BOOT}/{t_left}")
        g = gps_measure()
        if g:
            lg.a(f"boot: wait GPS first frame g = {str(g)}")
            # we don't even use this frame at all
            return
        lg.a(f"{t_left} seconds remaining GPS at boot")
        time.sleep(1)

    lg.a("warning: gps_boot_wait_first did NOT get GPS lock")


def _gps_read():
    _open_gps()
    b = bytes()
    till = time.perf_counter() + 2
    while time.perf_counter() < till:
        b = _g_sp.readall()
        if b:
            break
    _close_gps()
    # when bad signal, GPS frames come out empty, full of ','
    return b


def _gps_power_cycle():
    _u(STATE_DDS_GPS_POWER_CYCLE)
    t = 75
    lg.a(f"=== warning: power-cycling hat, wait ~{t} seconds ===")

    # GPIO26 controls the sixfab hat power rail
    # on() means high-level, shutdowns power to hat
    # off() means low-level, restores power to hat
    _pin = LED(26)
    _pin.on()
    time.sleep(5)
    _pin.off()
    time.sleep(t)
    lg.a("=== warning: power-cycling done, hat should be ON by now ===")


def _gps_measure():

    """
    returns (lat, lon, dt object, speed) or None
    for a dummy or real GPS measurement
    """

    # hooks
    if dds_get_cfg_flag_gps_error_forced():
        _u(STATE_DDS_BLE_APP_GPS_ERROR_POSITION)
        lg.a("debug: HOOK_GPS_ERROR_MEASUREMENT_FORCED")
        time.sleep(5)
        return

    if check_gps_dummy_mode():
        # lg.a('debug: HOOK_GPS_DUMMY_MEASUREMENT')
        time.sleep(0.5)
        fgp = dds_get_cfg_fake_gps_position()
        lat = "{:+.6f}".format(fgp[0])
        lon = "{:+.6f}".format(fgp[1])
        return lat, lon, datetime.datetime.utcnow(), 1

    # GPS state machine
    global _g_pu_gps
    global _g_pu_ctl
    g = None
    ns = -1
    try:
        b = _gps_read()

        # nothing came in from the port like, at all
        if not _g_bu353s4_port and not b:

            # maybe the GPS output was simply disabled
            _activate_gps_output()

            # try again
            b = _gps_read()

            # detect no output or strange thing with Linux USB ports
            if not b or (b'CPIN' in b):
                raise MyGpsException(f'bad GPS issue -> b = {b}')

        # detect RMC and GSV frames
        re_rmc = re.search(b"GPRMC(.*)\r\n", b)
        if re_rmc:
            g = _gps_parse_rmc_frame(b"$GPRMC" + re_rmc.group(1))
        re_gsv = re.search(b"GPGSV(.*)\r\n", b)
        if re_gsv:
            ns = _gps_parse_gsv_frame(b"$GPGSV" + re_gsv.group(1))

    except (Exception, ) as ex:
        if not _g_bu353s4_port and 'could not open port' in str(ex):
            raise MyGpsException('could not open GPS port')

    # GPS caches
    global _g_ts_cached_gps_valid_for
    global _g_cached_gps

    # number of satellites notification
    if 0 < ns <= 6 and is_it_time_to('SQS_gps_num_satellites', PERIOD_GPS_NOTI_NUM_GPS_SAT):
        notify_ddh_number_of_gps_satellites(ns)

    # OK frame
    if g:
        g = list(g)
        lat = "{:+.6f}".format(g[0])
        lon = "{:+.6f}".format(g[1])
        if g[3] == "":
            g[3] = "0"
        # float, float, datetime UTC, speed
        _u(f"{STATE_DDS_NOTIFY_GPS}/{lat}\n{lon}")
        now = time.perf_counter()
        _g_ts_cached_gps_valid_for = now + PERIOD_GPS_CACHE_VALID_SECS
        _g_cached_gps = lat, lon, g[2], float(g[3])
        return g

    # failed, and it's the first time ever
    # this mostly happens when DDH is booting
    if _g_ts_cached_gps_valid_for == 0:
        lg.a("failed and no cache ever yet")
        return

    # failed, but we have GPS cache and it's STILL VALID
    now = time.perf_counter()
    if now < _g_ts_cached_gps_valid_for:
        lat, lon, dt_utc, speed = _g_cached_gps
        _u(f"{STATE_DDS_NOTIFY_GPS}/{lat}\n{lon}")
        lg.a(f"using cached position {lat}, {lon}")
        return _g_cached_gps

    # this line is ESSENTIAL so we can act upon errors
    _g_cached_gps = None

    # failed, and cache is too OLD so INVALID
    global _g_banner_cache_too_old
    if now > _g_banner_cache_too_old:
        lg.a("failed, and cache is too old")
        _g_banner_cache_too_old = now + 300

    # tell GUI about GPS error
    _u(STATE_DDS_BLE_APP_GPS_ERROR_POSITION)
    time.sleep(3)


def gps_measure():
    try:
        g = _gps_measure()
        if g:
            return g

        # cache might be valid or just empty
        return _g_cached_gps

    except MyGpsException as ex:
        lg.a(f"error: gps_measure_inner() -> {ex}")
        if is_it_time_to("gps_power_cycle", PERIOD_GPS_POWER_CYCLE):
            lg.a(f'warning: power-cycling GPS')
            notify_ddh_error_hw_gps()
            _gps_power_cycle()

        lg.a(f'warning: auto-detecting GPS USB ports')
        global _g_pu_gps, _g_pu_ctl
        _g_pu_gps, _g_pu_ctl = detect_quectel_usb_ports()


    except (Exception,) as ex:
        lg.a(f"error: gps_measure_outer() -> {ex}")
