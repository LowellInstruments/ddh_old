from datetime import datetime
import json
import os
import subprocess as sp
import time
import pytz
import tzlocal
from dds.timecache import is_it_time_to
from mat.ble.ble_mat_utils import ble_mat_get_antenna_type_v2
from utils.logs import lg_sqs as lg
from utils.ddh_config import (dds_get_cfg_box_sn,
                              dds_get_cfg_box_project,
                              dds_get_cfg_vessel_name)
from utils.ddh_shared import (get_ddh_commit,
                              get_ddh_local_sw_version,
                              get_ddh_platform,
                              get_ddh_folder_path_sqs)

# these MUST match the ones in DDN file "sqs/notifications_v2.py"
DDH_NOTIFICATION_STATUS_BOOT = 'DDH just booted'
DDH_NOTIFICATION_STATUS_ALIVE = 'DDH is alive'
DDH_NOTIFICATION_STATUS_IN_PORT = 'DDH is around a port'
DDH_NOTIFICATION_STATUS_NEED_SW_UPDATE = 'DDH may use a software update'
DDH_NOTIFICATION_ERROR_HW_BLE = 'DDH had a Bluetooth error'
DDH_NOTIFICATION_ERROR_HW_GPS = 'DDH had a GPS error'
DDH_NOTIFICATION_ERROR_HW_LOGGER_OXYGEN = 'check oxygen sensor in logger'
DDH_NOTIFICATION_ERROR_HW_LOGGER_BATTERY = 'check battery in logger'
DDH_NOTIFICATION_ERROR_HW_LOGGER_PRESSURE = 'check pressure sensor in logger'
DDH_NOTIFICATION_ERROR_HW_LOGGER_RETRIES = 'too many bad download attempts on logger'
DDH_NOTIFICATION_ERROR_SW_AWS_S3 = 'too long since a good AWS sync'
DDH_NOTIFICATION_ERROR_SW_CRASH = 'DDH just crashed, or at least restarted'
DDH_NOTIFICATION_OK_LOGGER_DL = 'logger download OK'
DDH_NOTIFICATION_OK_LOGGER_HYPOXIA = 'logger detected hypoxia'
DDH_NOTIFICATION_SMS = 'DDH sent a SMS'


DDH_ALL_NOTIFICATIONS = [
    DDH_NOTIFICATION_STATUS_BOOT,
    DDH_NOTIFICATION_STATUS_ALIVE,
    DDH_NOTIFICATION_STATUS_IN_PORT,
    DDH_NOTIFICATION_STATUS_NEED_SW_UPDATE,
    DDH_NOTIFICATION_ERROR_HW_BLE,
    DDH_NOTIFICATION_ERROR_HW_GPS,
    DDH_NOTIFICATION_ERROR_HW_LOGGER_OXYGEN,
    DDH_NOTIFICATION_ERROR_HW_LOGGER_BATTERY,
    DDH_NOTIFICATION_ERROR_HW_LOGGER_PRESSURE,
    DDH_NOTIFICATION_ERROR_HW_LOGGER_RETRIES,
    DDH_NOTIFICATION_ERROR_SW_AWS_S3,
    DDH_NOTIFICATION_ERROR_SW_CRASH,
    DDH_NOTIFICATION_OK_LOGGER_DL,
    DDH_NOTIFICATION_OK_LOGGER_HYPOXIA,
    DDH_NOTIFICATION_SMS
]


class LoggerNotification:
    def __init__(self, mac, sn, kind, bat):
        self.mac = str(mac)
        self.sn = str(sn)
        self.kind = str(kind)
        self.bat = str(bat)
        # this is filled externally
        self.uuid_interaction = ''


class _DDHNotification:
    def __init__(self, s, g, ln: LoggerNotification, ver, extra):
        now = datetime.now()
        now_utc = datetime.utcnow()
        rv = sp.run("uptime -p", shell=True, stdout=sp.PIPE)
        up = rv.stdout.decode()
        
        rv = sp.run("awk '{print $1}' /proc/uptime", shell=True, stdout=sp.PIPE)
        up_int = rv.stdout.decode()

        self.msg_ver = ver
        self.reason = s
        self.time_local_epoch = int(now.timestamp())
        self.time_local_str = str(now).split('.')[0]
        self.time_utc_epoch = int(now_utc.timestamp())
        self.time_utc_str = str(now_utc).split('.')[0]
        self.time_zone_ddh = tzlocal.get_localzone_name()
        _o = datetime.now(pytz.timezone(self.time_zone_ddh)).strftime('%z')
        self.time_zone_offset = _o
        self.time_uptime_str = up.replace('\n', '')
        self.time_uptime_int_str = up_int.replace('\n', '')
        self.ddh_sw_commit = get_ddh_commit()
        self.ddh_sw_version = get_ddh_local_sw_version()
        self.ddh_gps_position = ''
        self.ddh_gps_speed = ''
        _, self.ddh_ble_antenna = ble_mat_get_antenna_type_v2()
        if g:
            lat, lon, _, speed = g
            self.ddh_gps_position = '{:.4f}, {:.4f}'.format(float(lat), float(lon))
            self.ddh_gps_speed = '{:.2f} knots'.format(float(speed))
        self.ddh_box_name = dds_get_cfg_vessel_name()
        self.ddh_box_sn = dds_get_cfg_box_sn()
        self.ddh_box_project = dds_get_cfg_box_project()
        self.ddh_platform = get_ddh_platform()
        self.logger_mac = ""
        self.logger_sn = ""
        self.logger_type = ""
        self.logger_bat = ""
        if ln:
            self.logger_mac = ln.mac
            self.logger_sn = ln.sn
            self.logger_type = ln.kind
            self.logger_bat = ln.bat
            self.uuid_interaction = ln.uuid_interaction
        self.extra = str(extra)

    def display_details(self):
        if self.logger_mac:
            s = "notification details: {} for logger {} ({}) at {}"
            lg.a(s.format(self.reason,
                          self.logger_sn,
                          self.logger_mac,
                          self.ddh_gps_position))
        else:
            s = "notification details: {} at {}"
            lg.a(s.format(self.reason,
                          self.ddh_gps_position))

    def to_file(self):
        # generate a SQS FILE from dict, its content is JSON
        fol = str(get_ddh_folder_path_sqs())
        now = int(time.time_ns())
        path = "{}/{}.sqs".format(fol, now)
        with open(path, "w") as f:
            json.dump(vars(self), f, indent=4)
        lg.a(f"generated SQS file {path}, details next")
        self.display_details()


def _n(s, g='', ln=None, v=2, extra=''):
    if s not in DDH_ALL_NOTIFICATIONS:
        print(f'ddh_notification unknown opcode {s}')
        return
    n = _DDHNotification(s, g, ln, v, extra)
    n.to_file()


def notify_logger_download(g, ln):
    return _n(DDH_NOTIFICATION_OK_LOGGER_DL, g, ln)


def notify_boot(g):
    return _n(DDH_NOTIFICATION_STATUS_BOOT, g)


def notify_logger_error_sensor_pressure(g, ln):
    return _n(DDH_NOTIFICATION_ERROR_HW_LOGGER_PRESSURE, g, ln)


def notify_logger_error_low_battery(g, ln):
    return _n(DDH_NOTIFICATION_ERROR_HW_LOGGER_BATTERY, g, ln)


def notify_error_sw_aws_s3():
    return _n(DDH_NOTIFICATION_ERROR_SW_AWS_S3)


def notify_error_sw_crash():
    return _n(DDH_NOTIFICATION_ERROR_SW_CRASH)


def notify_ddh_alive(g):
    if is_it_time_to("ddh_notification_alive", 3600 * 12):
        return _n(DDH_NOTIFICATION_STATUS_ALIVE, g)


def notify_ddh_error_hw_ble(g):
    return _n(DDH_NOTIFICATION_ERROR_HW_BLE, g)


def notify_ddh_error_hw_gps():
    return _n(DDH_NOTIFICATION_ERROR_HW_GPS)


def notify_ddh_in_port(g):
    return _n(DDH_NOTIFICATION_STATUS_IN_PORT, g)


def notify_logger_dox_hypoxia(g, ln):
    return _n(DDH_NOTIFICATION_OK_LOGGER_HYPOXIA, g, ln)


def notify_logger_error_retries(g, ln):
    return _n(DDH_NOTIFICATION_ERROR_HW_LOGGER_RETRIES, g, ln)


def notify_logger_error_sensor_oxygen(g, ln):
    return _n(DDH_NOTIFICATION_ERROR_HW_LOGGER_OXYGEN, g, ln)


def notify_ddh_needs_sw_update(g):
    try:
        vl = get_ddh_local_sw_version()

        # get github version
        s = '.ddh_version'
        c = f'wget https://raw.githubusercontent.com/LowellInstruments/ddh/master/{s}'
        c += f' -O /tmp/{s}'
        rv = sp.run(c, shell=True, stdout=sp.PIPE, stderr=sp.PIPE)
        if rv.returncode:
            lg.a('error: cannot obtain remote DDH version')
            # 0 so we don't signal we need update
            return 0

        with open(f'/tmp/{s}', 'r') as f:
            vg = f.readline().replace('\n', '')

        if vl < vg:
            _n(DDH_NOTIFICATION_STATUS_NEED_SW_UPDATE, g)
            return 1

    except (Exception, ) as ex:
        lg.a(f'error: sqs_msg_ddh_needs_update -> {ex}')


def notify_via_sms(s):
    return _n(DDH_NOTIFICATION_SMS, g='', ln=None, v=2, extra=s)


if __name__ == '__main__':
    os.chdir('..')
    _n(DDH_NOTIFICATION_STATUS_ALIVE)
