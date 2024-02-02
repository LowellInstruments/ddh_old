import subprocess as sp
import glob
import os
import uuid
import boto3
import time
import json
from dds.ddn_msg import (
    DdnMsg,
    OPCODE_SQS_LOGGER_LOW_BATTERY,
    OPCODE_SQS_DDH_ALIVE,
    OPCODE_SQS_DDH_ERROR_BLE_HW,
    OPCODE_SQS_DDH_BOOT,
    OPCODE_SQS_DDH_ERROR_GPS_HW,
    OPCODE_SQS_LOGGER_DL_OK,
    OPCODE_SQS_LOGGER_MAX_ERRORS,
    OPCODE_SQS_LOGGER_ERROR_OXYGEN, OPCODE_SQS_DDH_NEEDS_UPDATE
)
from dds.net import ddh_get_internet_via

from dds.timecache import its_time_to
from mat.utils import linux_is_rpi3, linux_is_rpi4
from settings import ctx
from utils.logs import lg_sqs as lg
from utils.ddh_shared import (
    get_ddh_folder_path_sqs,
    get_ddh_commit,
    dds_get_json_vessel_name,
    get_utc_offset
)
import warnings

warnings.filterwarnings("ignore",
                        category=FutureWarning,
                        module="botocore.client")


# ------------------------------------
# allows for double credential system
# ------------------------------------
sqs_key_id = os.getenv("DDH_AWS_KEY_ID")
custom_sqs_key_id = os.getenv("DDH_CUSTOM_SQS_KEY_ID")
if custom_sqs_key_id:
    sqs_key_id = custom_sqs_key_id
sqs_access_key = os.getenv("DDH_AWS_SECRET")
custom_sqs_access_key = os.getenv("DDH_CUSTOM_SQS_ACCESS_KEY")
if custom_sqs_access_key:
    sqs_access_key = custom_sqs_access_key


sqs = boto3.client(
    "sqs",
    region_name="us-east-2",
    aws_access_key_id=sqs_key_id,
    aws_secret_access_key=sqs_access_key,
)


def dds_create_folder_sqs():
    r = get_ddh_folder_path_sqs()
    os.makedirs(r, exist_ok=True)


def _sqs_gen_file_for_tests():

    # build DDN message
    d = DdnMsg()
    d.reason = OPCODE_SQS_LOGGER_LOW_BATTERY
    d.project = "DEF"
    d.logger_mac = "ff:ff:ff:dd:ee:ff"
    d.logger_sn = "8888888"
    d.vessel = "maggiesue"
    d.ddh_commit = "akfjdhlakdjfh"
    d.utc_time = int(time.time())
    d.local_time = int(d.utc_time + get_utc_offset())
    d.box_sn = "5454545"
    d.hw_uptime = "lots of times"
    d.gps_position = "{},{}".format("10.10101", "66.66666")
    d.platform = "rpi6"
    d.msg_ver = "mv1"
    d.data = "data1234data"

    # convert DDNMsg to dict
    d = vars(d)

    # generate a SQS FILE from dict, its content is JSON
    fol = str(get_ddh_folder_path_sqs())
    now = int(time.time())
    path = "{}/{}.sqs".format(fol, now)
    with open(path, "w") as f:
        json.dump(d, f)

    print("done _sqs_gen_file_for_test()")


def _sqs_gen_file(desc, mac, lg_sn, lat, lon, m_ver=1, data=""):

    # grab all local info
    try:
        vn = dds_get_json_vessel_name()
    except (Exception,):
        vn = "test_vessel_name"
    try:
        dch = get_ddh_commit()
    except (Exception,):
        dch = "test_ddh_commit"
    rv_up = sp.run("uptime", shell=True, stdout=sp.PIPE, stderr=sp.PIPE)
    plat = "dev"
    if linux_is_rpi3():
        plat = "rpi3"
    elif linux_is_rpi4():
        plat = "rpi4"

    # build DDN message w/ local info + parameters
    d = DdnMsg()
    d.reason = desc
    d.project = os.getenv("DDH_BOX_PROJECT_NAME")
    d.logger_mac = mac
    d.logger_sn = lg_sn
    d.vessel = vn
    d.ddh_commit = dch
    d.utc_time = int(time.time())
    d.local_time = int(d.utc_time + get_utc_offset())
    d.box_sn = os.getenv("DDH_BOX_SERIAL_NUMBER")
    d.hw_uptime = rv_up.stdout.decode()
    d.gps_position = "{},{}".format(lat, lon)
    d.platform = plat
    d.msg_ver = m_ver
    d.data = data

    # convert DDN msg to dict
    d = vars(d)

    # generate a SQS FILE from dict, its content is JSON
    fol = str(get_ddh_folder_path_sqs())
    now = int(time.time_ns())
    path = "{}/{}.sqs".format(fol, now)
    with open(path, "w") as f:
        json.dump(d, f)

    # log the kind of generated file (logger / DDH)
    s = "generated file {}, details below"
    lg.a(s.format(path))
    if mac:
        s = "{} for logger {} ({}) at {}, {}"
        lg.a(s.format(desc, lg_sn, mac, lat, lon))
    else:
        s = "{} at {}, {}"
        lg.a(s.format(desc, lat, lon))


def sqs_msg_ddh_booted(*args):
    _sqs_gen_file(OPCODE_SQS_DDH_BOOT, "", "", *args)


def sqs_msg_ddh_needs_update(*args):

    try:
        s = '.ddh_version'
        # get local version
        with open(s, 'r') as f:
            vl = f.readline().replace('\n', '')

        # get github version
        c = f'wget https://raw.githubusercontent.com/LowellInstruments/ddh/master/{s}'
        c += f' -O /tmp/{s}'
        rv = sp.run(c, shell=True, stdout=sp.PIPE, stderr=sp.PIPE)
        if rv.returncode == 0:
            with open(f'/tmp/{s}', 'r') as f:
                vg = f.readline().replace('\n', '')

            if vl < vg:
                _sqs_gen_file(OPCODE_SQS_DDH_NEEDS_UPDATE, "", "", *args)
                return 1

    except (Exception, ) as ex:
        lg.a(f'error: sqs_msg_ddh_needs_update -> {ex}')


def sqs_msg_ddh_alarm_s3():
    # hardcoded opcode so deployed DDH w/ old LIU library don't crash
    mac = ''
    lg_sn = ''
    lat = ''
    lon = ''
    data = ''
    _sqs_gen_file('DDH_ALARM_S3', mac, lg_sn, lat, lon, m_ver=1, data=data)


def sqs_msg_ddh_alive(*args):
    if its_time_to("send_sqs_ddh_alive_msg", 3600 * 12):
        _sqs_gen_file(OPCODE_SQS_DDH_ALIVE, "", "", *args)


def sqs_msg_ddh_error_ble_hw(*args):
    _sqs_gen_file(OPCODE_SQS_DDH_ERROR_BLE_HW, "", "", *args)


def sqs_msg_ddh_error_gps_hw(*args):
    _sqs_gen_file(OPCODE_SQS_DDH_ERROR_GPS_HW, "", "", *args)


def sqs_msg_logger_download(*args):
    _sqs_gen_file(OPCODE_SQS_LOGGER_DL_OK, *args)


def sqs_msg_logger_error_max_retries(*args):
    _sqs_gen_file(OPCODE_SQS_LOGGER_MAX_ERRORS, *args)


def sqs_msg_logger_error_oxygen_zeros(*args):
    _sqs_gen_file(OPCODE_SQS_LOGGER_ERROR_OXYGEN, *args)


def sqs_msg_logger_low_battery(*args):
    _sqs_gen_file(OPCODE_SQS_LOGGER_LOW_BATTERY, *args)


def sqs_msg_sms():
    # we do it here so old versions don't crash
    # from liu.ddn_msg import OPCODE_SQS_SMS
    mac = ''
    lg_sn = '6666666'
    lat = '0.000000'
    lon = '0.000000'
    data = 'sms'
    _sqs_gen_file('DDH_SMS_TEST', mac, lg_sn, lat, lon, m_ver=1, data=data)


def sqs_msg_ddh_alarm_crash(s):
    # hardcoded opcode so deployed DDH w/ old LIU library don't crash
    mac = ''
    lg_sn = ''
    lat = ''
    lon = ''
    data = f'sms/{s}'
    _sqs_gen_file('DDH_SMS_CRASH', mac, lg_sn, lat, lon, m_ver=1, data=data)


def sqs_msg_notes_cc26x2r(*args):
    notes, mac, sn, lat, lon = args
    v = notes["battery_level"]
    if v < 1800:
        sqs_msg_logger_low_battery(mac, sn, lat, lon)


def sqs_serve():

    # this runs from time to time, not always
    if not its_time_to("sqs_serve", 600):
        return

    if not ctx.sqs_en:
        lg.a("warning: ctx.sqs_en is False")
        return

    if ddh_get_internet_via() == "none":
        # prevents main_loop getting stuck
        lg.a("warning: no internet to serve SQS")
        return

    # ---------------------------------
    # grab / collect SQS files to send
    # ---------------------------------
    fol = get_ddh_folder_path_sqs()
    files = glob.glob("{}/*.sqs".format(fol))
    if files:
        lg.a("---------------------")
        lg.a("serving {} SQS files".format(len(files)))
        lg.a("---------------------\n")

    for _ in files:

        # this happens not often but did once
        if os.path.getsize(_) == 0:
            os.unlink(_)
            continue

        # reads local SQS file as JSON
        f = open(_, "r")
        j = json.load(f)
        lg.a("serving file {}".format(_))

        try:
            # ENQUEUES the JSON as string to SQS service
            m = json.dumps(j)
            rsp = sqs.send_message(
                QueueUrl=os.getenv("DDH_SQS_QUEUE_NAME"),
                MessageGroupId=str(uuid.uuid4()),
                MessageDeduplicationId=str(uuid.uuid4()),
                MessageBody=m,
            )

            md = rsp["ResponseMetadata"]
            if md and int(md["HTTPStatusCode"]) == 200:
                lg.a("debug: SQS OK sent msg\n\n{}\n".format(m))
                # delete SQS file
                os.unlink(_)

        except (Exception,) as ex:
            lg.a("error sqs_serve: {}".format(ex))
        finally:
            if f:
                f.close()


if __name__ == "__main__":
    # this file can be tested in main_dds.py
    pass
