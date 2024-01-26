import datetime
import subprocess as sp
import time
import serial
from dds.sqs import sqs_msg_ddh_error_gps_hw
from dds.timecache import its_time_to
from mat.gps import PORT_CTRL, PORT_DATA
from mat.utils import linux_is_rpi, linux_set_datetime
from tzlocal import get_localzone

from utils.ddh_config import dds_get_cfg_vessel_name, dds_get_cfg_flag_gps_external, dds_get_cfg_flag_gps_error_forced, \
    dds_get_cfg_fake_gps_position
from utils.ddh_shared import (
    send_ddh_udp_gui as _u,
    STATE_DDS_NOTIFY_GPS,
    STATE_DDS_BLE_APP_GPS_ERROR_POSITION,
    STATE_DDS_NOTIFY_GPS_NUM_SAT,
    STATE_DDS_NOTIFY_GPS_BOOT,
    STATE_DDS_NOTIFY_BOAT_NAME,
    STATE_DDS_NOTIFY_GPS_CLOCK,
    STATE_DDS_GPS_POWER_CYCLE, check_gps_dummy_mode,
)
from utils.logs import lg_gps as lg
import re
from gpiozero import LED

from utils.find_usb_port_auto import find_usb_port_automatically

_g_ts_cached_gps_valid_for = 0
_g_cached_gps = None
_g_banner_cache_too_old = 0
_g_ever_gps_clock_sync = False


PERIOD_GPS_CACHE_VALID_SECS = 30
PERIOD_GPS_TELL_NUM_SATS_SECS = 300
PERIOD_GPS_TELL_VESSEL_SECS = 30
PERIOD_GPS_AT_BOOT_SECS = 300
PERIOD_GPS_TELL_GPS_HW_ERROR_SECS = 3600 * 3
PERIOD_GPS_TELL_PUCK_NO_PC = 3600 * 6
PERIOD_GPS_POWER_CYCLE = 300


# todo -=--> move check_gps_dummy_mode() here and only check once

def _gps_ll_check_hat_out_stream():
    # ll: stands for 'low-level'
    def _check():
        # give time to accumulate GPS data
        time.sleep(1)
        c = "cat {}".format(PORT_DATA)
        rv = sp.run(c, shell=True, stdout=sp.PIPE, stderr=sp.PIPE)
        return b"$GPRMC" in rv.stdout

    try:
        return _check()
    except Exception as ex:
        lg.a("error: gps_ll_check_hat_out_stream() -> {}".format(ex))


def _gps_bu353s4_find_usb_port():
    # the GPS USB puck has 2 PIDs
    p = find_usb_port_automatically('067B:2303')
    if p:
        return p
    # try the other one
    return find_usb_port_automatically('067B:23A3')


if dds_get_cfg_flag_gps_external():
    _g_bu353s4_port = _gps_bu353s4_find_usb_port()


def _coord_decode(coord: str):
    # src: stackoverflow 18442158 latitude format
    x = coord.split(".")
    head = x[0]
    deg = head[:-2]
    minutes = "{}.{}".format(head[-2:], x[1])
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
    lat = _coord_decode(s[3])
    dir_lat = s[4]
    lon = _coord_decode(s[5])
    dir_lon = s[6]
    speed = s[7]
    _course = s[8]
    # variation = s[10]

    # GPS date and time are UTC
    fmt = "{} {}".format(_day, _t)
    gps_time = datetime.datetime.strptime(fmt, "%d/%m/%y %H:%M:%S")

    # display
    # print('time {} date {} lat {} lon {}'.format(_t, _day, lat, lon))
    # print('speed {} mag_var {} course {}'.format(speed, variation, _course))

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

    # save to disk for other apps
    # d = {
    #    "lat": lat,
    #    "lon": lon,
    #    "gps_time": gps_time,
    #    "speed": speed
    # }
    # j = json.dumps(d)
    # with open("/tmp/gps_last.json", "w") as outfile:
    #    outfile.write(j)

    # everything went OK
    return lat, lon, gps_time, speed


def _gps_parse_gsv_frame(data: bytes, force_print=False):
    """
    parse fields in a GSV NMEA string
    """

    # data: b'$GPGSV,...,$GPGGA,...' all mixed
    if b"GPGSV" not in data:
        return

    # $GPGSV, #messages, msg_num, num sat, ...
    data = data.decode()
    data = data.split(",")
    idx = data.index("$GPGSV")
    data = data[idx:]

    # log satellites but not always
    try:
        n = int(data[3])
        if force_print or its_time_to("show_gsv_frame", PERIOD_GPS_TELL_NUM_SATS_SECS):
            _u("{}/{}".format(STATE_DDS_NOTIFY_GPS_NUM_SAT, n))
            if n < 7:
                lg.a("{} satellites in view".format(n))

    except (Exception,) as ex:
        lg.a("error: parse GSV frame {} -> {}".format(data, ex))


def _gps_measure():
    """
    returns (lat, lon, dt object, speed) or None
    for a dummy or real GPS measurement
    """

    global _g_bu353s4_port

    # hooks
    if dds_get_cfg_flag_gps_error_forced():
        _u(STATE_DDS_BLE_APP_GPS_ERROR_POSITION)
        lg.a("debug: HOOK_GPS_ERROR_MEASUREMENT_FORCED")
        return

    if check_gps_dummy_mode():
        # lg.a('debug: HOOK_GPS_DUMMY_MEASUREMENT')
        time.sleep(0.5)
        fgp = dds_get_cfg_fake_gps_position()
        lat = "{:+.6f}".format(fgp[0])
        lon = "{:+.6f}".format(fgp[1])
        return lat, lon, datetime.datetime.utcnow(), 1

    # open serial port
    if dds_get_cfg_flag_gps_external():
        sp = serial.Serial(_g_bu353s4_port, 4800, timeout=0.2)
    else:
        sp = serial.Serial(PORT_DATA, baudrate=115200, timeout=0.2,
                           rtscts=True, dsrdtr=True)
    sp.flushInput()

    global _g_ts_cached_gps_valid_for
    global _g_cached_gps
    now = time.perf_counter()

    # try to flush stuff
    sp.readall()
    sp.flushInput()
    g = []

    # =============================
    # loop waiting for GPS frames
    # =============================
    till = time.perf_counter() + 2
    while 1:
        if time.perf_counter() > till:
            break

        # --------------------------
        # do NOT use sp.readlines()
        # --------------------------
        g = []
        b = sp.readall()

        # USB GPS puck
        if dds_get_cfg_flag_gps_external():
            if not b:
                continue
            try:
                # just see we can decode the thing
                b.decode()
            except (Exception,):
                continue

            # detect and parse the type of GPS frame
            re_rmc = re.search(b"GPRMC(.*)\r\n", b)
            if re_rmc:
                g = _gps_parse_rmc_frame(b"$GPRMC" + re_rmc.group(1))
            re_gsv = re.search(b"GPGSV(.*)\r\n", b)
            if re_gsv:
                _gps_parse_gsv_frame(b"$GPGSV" + re_gsv.group(1))

        # GPS shield
        else:
            _gps_parse_gsv_frame(b)
            g = _gps_parse_rmc_frame(b)

        if g:
            break

    # close serial port
    if sp:
        sp.close()

    # OK frame
    if g:
        g = list(g)
        lat = "{:+.6f}".format(g[0])
        lon = "{:+.6f}".format(g[1])
        if g[3] == "":
            g[3] = "0"
        # float, float, datetime UTC, speed
        _u("{}/{}, {}".format(STATE_DDS_NOTIFY_GPS, lat, lon))
        _g_ts_cached_gps_valid_for = now + PERIOD_GPS_CACHE_VALID_SECS
        _g_cached_gps = lat, lon, g[2], float(g[3])
        return g

    # failed, and it's the first time ever
    # this mostly happens when DDH is booting
    if _g_ts_cached_gps_valid_for == 0:
        lg.a("failed, and no cache ever yet")
        return

    # failed, but we have GPS cache and it's STILL VALID
    now = time.perf_counter()
    if now < _g_ts_cached_gps_valid_for:
        lat, lon, dt_utc, speed = _g_cached_gps
        _u("{}/{}, {}".format(STATE_DDS_NOTIFY_GPS, lat, lon))
        lg.a("using cached position {}, {}".format(lat, lon))
        return _g_cached_gps

    # failed, and also the cache is too OLD
    global _g_banner_cache_too_old
    if now > _g_banner_cache_too_old:
        lg.a("failed, and cache is too old")
        _g_banner_cache_too_old = now + 300
    _g_cached_gps = "", "", None, float(0)

    # tell GUI about GPS error
    _u(STATE_DDS_BLE_APP_GPS_ERROR_POSITION)


def gps_measure():
    try:
        g = _gps_measure()
        if g:
            return g

        # at this point, cache may be valid or just empty
        return _g_cached_gps

    except (Exception,) as ex:
        lg.a("error: gps_measure() -> {}".format(ex))


def gps_clock_sync_if_so(dt_gps_utc) -> bool:
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
    lg.a("debug: gps_cloc_sync_diff_secs = {}".format(diff_secs))
    z_my = get_localzone()
    z_utc = datetime.timezone.utc
    dt_my = dt_gps_utc.replace(tzinfo=z_utc).astimezone(tz=z_my)
    t = str(dt_my)[:-6]

    # this is a bool
    if linux_set_datetime(t):
        _g_ever_gps_clock_sync = True
        return True
    return False


def gps_wait_for_first_frame_at_boot():

    # Wikipedia: GPS-Time-To-First-Fix for cold start is typ.
    # 2 to 5 minutes, warm <= 45 secs, hot <= 22 secs

    till = time.perf_counter() + PERIOD_GPS_AT_BOOT_SECS
    s = "boot: wait up to {} seconds"
    lg.a(s.format(PERIOD_GPS_AT_BOOT_SECS))

    while 1:
        t = time.perf_counter()
        if t > till:
            break

        # ----------------------------------------------
        # MEASURE countdown at boot time to connect GPS
        # ----------------------------------------------
        t = int(till - time.perf_counter())
        t = t if t > 0 else 0
        _u("{}/{}".format(STATE_DDS_NOTIFY_GPS_BOOT, t))

        # this GPS measure call controls exceptions :)
        g = gps_measure()
        if g:
            lg.a("gps_wait_at_boot returned {}".format(g))
            return g
        lg.a("{} seconds left to wait for GPS at boot".format(t))
        time.sleep(1)

    lg.a("warning: gps_wait_at_boot could not get GPS lock")
    return "", "", None, 0


def gps_tell_vessel_name():
    if not its_time_to("tell_vessel_name", PERIOD_GPS_TELL_VESSEL_SECS):
        return
    v = dds_get_cfg_vessel_name()
    _u("{}/{}".format(STATE_DDS_NOTIFY_BOAT_NAME, v))


def gps_tell_position_logger(g):
    lat, lon, tg, speed = g
    s = "logger process at {}, {}, speed {}"
    lg.a(s.format(lat, lon, speed))


def gps_hw_error(g) -> int:
    if g:
        # no error
        return 0

    # don't tell GPS error too often
    if its_time_to("tell_gps_hw_error", PERIOD_GPS_TELL_GPS_HW_ERROR_SECS):
        lg.a("error: no GPS frame, examine further log messages")
        sqs_msg_ddh_error_gps_hw("", "")
        return 1

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


def gps_print_trying_clock_sync_at_boot():
    if not check_gps_dummy_mode():
        lg.a("trying clock sync via GPS at boot")
        return
    lg.a("warning: dummy GPS, not syncing clock via GPS at boot")


def gps_did_we_ever_clock_sync() -> bool:
    _u(STATE_DDS_NOTIFY_GPS_CLOCK)
    return _g_ever_gps_clock_sync


def _gps_power_on_off_hat():
    _u("{}".format(STATE_DDS_GPS_POWER_CYCLE))
    t = 75
    lg.a("=== warning: power-cycling hat, wait ~{} seconds ===".format(t))

    # GPIO26 controls the sixfab hat power rail
    _pin = LED(26)

    # on() means high-level, shutdowns power to hat
    _pin.on()
    time.sleep(5)

    # off() means low-level, restores power to hat
    _pin.off()
    time.sleep(t)
    lg.a("=== warning: power-cycling done, hat should be ON by now ===")


def gps_power_cycle_if_so(forced=False):

    # don't do this too often
    if not forced and not its_time_to(
            "check_we_need_gps_power_cycle", PERIOD_GPS_POWER_CYCLE):
        return

    if check_gps_dummy_mode():
        lg.a("debug: no power cycle dummy GPS")
        return

    if dds_get_cfg_flag_gps_external():
        if its_time_to("show_debug_power_cycle_gps_puck", PERIOD_GPS_TELL_PUCK_NO_PC):
            lg.a("debug: no power cycle BU-353-S4 GPS puck")
        return

    # ------------------------
    # see need to power cycle
    # ------------------------
    sp = None
    try:
        # open serial port
        sp = serial.Serial(
            PORT_CTRL, baudrate=115200, timeout=1, rtscts=True, dsrdtr=True
        )
        sp.flushInput()
        sp.readall()

        # query hat about GPS output stream
        sp.write(b"AT+QGPS?\r")
        ans = sp.readall()

        # output stream seems OK
        if b"\r\n+QGPS: 1\r\n\r\nOK\r\n" in ans:
            # be really sure hat is OK
            if not _gps_ll_check_hat_out_stream():
                lg.a("error: power-cycle needed, no GPS OUT stream")
                _gps_power_on_off_hat()

        # output stream answers but not enabled, enable it
        elif b"\r\n+QGPS: 0\r\n\r\nOK\r\n" in ans:
            sp.readall()
            sp.write(b"AT+QGPS=1\r")
            ans = sp.readall()
            if b"\r\nOK\r\n" in ans:
                lg.a("OK: power check, hat set did 0 -> 1")
            else:
                e = "error: power check, cannot set to 1 -> {}"
                lg.a(e.format(ans))

        # output stream not even there, but at least port answers
        elif not ans:
            lg.a("warning: power-cycle needed, hat not answering")
            _gps_power_on_off_hat()

        else:
            lg.a("warning: power-cycle, this should never happen")

    except (Exception,) as ex:
        # port does not even answer at /dev/ttyUSBx
        lg.a("error: failed gps_power_cycle -> {}".format(ex))
        _gps_power_on_off_hat()

    finally:
        if sp:
            sp.close()

    # easy with next functions
    time.sleep(1)


def gps_configure_shield():

    if check_gps_dummy_mode():
        return

    if dds_get_cfg_flag_gps_external():
        return

    did_configure_ok = False
    _sp = None

    try:
        _sp = serial.Serial(
            PORT_CTRL, baudrate=115200, timeout=1, rtscts=True, dsrdtr=True
        )
        _sp.flushInput()
        _sp.readall()
        _sp.write(b"AT+QGPS?\r")
        ans = _sp.readall()

        # ------------------------------------
        # check GPS output stream is enabled
        # ------------------------------------
        if b"\r\n+QGPS: 0\r\n\r\nOK\r\n" in ans:
            _sp.write(b"AT+QGPS=1\r")
            ans = _sp.readall()
            if b"\r\nOK\r\n" in ans:
                lg.a("OK: configure_if_so set hat 0 -> 1")
                did_configure_ok = True
            else:
                e = "error: configure_if_so cannot set to 1 -> {}"
                lg.a(e.format(ans))

        elif b"\r\n+QGPS: 1\r\n\r\nOK\r\n" in ans:
            did_configure_ok = True

    except (Exception,) as ex:
        lg.a("error: configure_if_so -> {}".format(ex))

    finally:
        if _sp:
            _sp.close()

    return did_configure_ok


def gps_know_hat_firmware_version():

    if check_gps_dummy_mode():
        return

    if dds_get_cfg_flag_gps_external():
        return

    sp = None
    try:
        sp = serial.Serial(
            PORT_CTRL, baudrate=115200, timeout=1, rtscts=True, dsrdtr=True
        )
        sp.flushInput()
        sp.readall()
        sp.write(b"AT+CVERSION\r")
        ans_v = sp.readall()
        sp.write(b"AT+QGMR\r")
        ans_m = sp.readall()
        ans_v = ans_v.replace(b"OK", b"")
        ans_v = ans_v.replace(b"\r\n", b"")
        ans_m = ans_m.replace(b"OK", b"")
        ans_m = ans_m.replace(b"\r\n", b"")
        if ans_v:
            lg.a("debug: firmware CVERSION {}".format(ans_v))
        else:
            lg.a("error: firmware CVERSION")
        if ans_m:
            lg.a("debug: firmware GMR {}".format(ans_m))
        else:
            lg.a("error: firmware GMR")

    except (Exception,) as ex:
        lg.a("error: hat_firmware_version -> {}".format(ex))

    finally:
        if sp:
            sp.close()

    time.sleep(0.1)


if __name__ == "__main__":
    if not dds_get_cfg_flag_gps_external():
        gps_configure_shield()
    while 1:
        m = gps_measure()
        print(m)
