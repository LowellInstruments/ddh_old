#!/usr/bin/env python3
import datetime
import glob
import json
import multiprocessing
import os
import subprocess as sp
import sys
import time
from multiprocessing import Process
import setproctitle
from dds.emolt import this_box_has_grouped_s3_uplink
from dds.notifications import notify_error_sw_aws_s3
from dds.timecache import its_time_to
from mat.linux import linux_is_process_running
from mat.utils import linux_is_rpi
from utils.ddh_config import dds_get_cfg_vessel_name, dds_get_cfg_aws_en, dds_get_cfg_aws_credential
from utils.ddh_shared import (
    send_ddh_udp_gui as _u,
    get_ddh_folder_path_dl_files,
    STATE_DDS_NOTIFY_CLOUD_LOGIN,
    STATE_DDS_NOTIFY_CLOUD_BUSY,
    STATE_DDS_NOTIFY_CLOUD_ERR,
    STATE_DDS_NOTIFY_CLOUD_OK,
    dds_get_aws_has_something_to_do_via_gui_flag_file, get_ddh_file_path_ts_aws, ddh_get_db_status_file
)
from utils.logs import lg_aws as lg

g_fresh_boot = 1
PERIOD_AWS_S3_SECS = 3600 * 6
PERIOD_ALARM_AWS_S3 = 86400 * 7
AWS_S3_SYNC_PROC_NAME = "dds_aws_sync"
dev = not linux_is_rpi()
past_n_files = 0


def _get_aws_bin_path():
    # apt install awscli
    # 2024 is 1.22.34
    return "aws"


def ddh_write_aws_sqs_ts(k, v):
    assert k in ('aws', 'sqs')

    # epoch utc
    t = int(time.time())
    # in API code, this path is also used
    p = ddh_get_db_status_file()

    # load the file or get custom content
    try:
        with open(p, 'r') as f:
            j = json.load(f)
    except (Exception, ):
        j = {
            'aws': ('unknown', t),
            'sqs': ('unknown', t)
        }

    # update file content
    try:
        j[k] = (v, t)
        with open(p, 'w') as f:
            json.dump(j, f)
    except (Exception, ):
        lg.a(f'error: cannot record AWS / SQS state to {p}')


# ------------------------------------------
# we use _ts() functions to track the
# last time AWS sync went OK and
# generate an alarm if too long w/o success
# ------------------------------------------


def _touch_s3_ts():
    # ts: timestamp
    p = get_ddh_file_path_ts_aws()
    with open(p, 'w') as f:
        f.write(str(int(time.time())))


def _get_s3_ts():
    p = get_ddh_file_path_ts_aws()
    try:
        with open(p, 'r') as f:
            return f.readline()
    except FileNotFoundError:
        # first time ever
        lg.a(f'warning: AWS timestamp file not found {p}')
        return 0


def _aws_s3_sync_process():

    # useful on RPi3 to prevent BLE and AWS (wi-fi) collisions
    global g_fresh_boot
    if g_fresh_boot:
        lg.a("debug: AWS politely waiting upon boot")
        g_fresh_boot = 0
        time.sleep(30)
        lg.a("debug: AWS politely resuming after boot")

    # sys.exit() instead of return prevents zombie processes
    setproctitle.setproctitle(AWS_S3_SYNC_PROC_NAME)
    fol_dl_files = get_ddh_folder_path_dl_files()
    _k = dds_get_cfg_aws_credential("cred_aws_key_id")
    _s = dds_get_cfg_aws_credential("cred_aws_secret")
    _n = dds_get_cfg_aws_credential("cred_aws_bucket")
    if _k is None or _s is None or _n is None:
        lg.a("warning: missing credentials")
        _u(STATE_DDS_NOTIFY_CLOUD_LOGIN)
        sys.exit(1)

    if not _n.startswith("bkt-"):
        lg.a('warning: bucket name does not start with bkt-')

    # prepare to run it
    _u(STATE_DDS_NOTIFY_CLOUD_BUSY)
    _bin = _get_aws_bin_path()
    dr = "--dryrun" if dev else ""

    # get list of macs within dl_files folder
    ms = [d for d in glob.glob(str(fol_dl_files) + '/*') if os.path.isdir(d)]
    all_rv = 0
    for m in ms:
        # um: dl_files/ddh#red_feet, we need to lose 'dl_files'
        um = m.replace('dl_files/', '')
        c = (
            "AWS_ACCESS_KEY_ID={} AWS_SECRET_ACCESS_KEY={} "
            "{} s3 sync {} s3://{}/{} "
            '--exclude "*" '
            '--include "*.csv" '
            '--include "*.gps" '
            '--include "*.lid" '
            '--include "*.bin" '
            '--exclude "test_*.csv" '
            '--exclude "test_*.lid" '
            '--include "*.txt" {}'
        ).format(_k, _s, _bin, m, _n, um, dr)

        if this_box_has_grouped_s3_uplink():
            v = dds_get_cfg_vessel_name()
            # v: "bailey's" --> BAYLEYS
            v = v.replace("'", "")
            v = v.replace(" ", "_")
            v = v.upper()
            # um: dl_files/ddh#red_feet, we lose dl_files and group
            y = datetime.datetime.utcnow().year
            um = m.replace('dl_files', "{}/{}".format(str(y), v))
            c = (
                "AWS_ACCESS_KEY_ID={} AWS_SECRET_ACCESS_KEY={} "
                "{} s3 sync {} s3://{}/{} "
                '--exclude "*" '
                '--include "*.csv" '
                '--include "*.gps" '
                '--include "*.lid" '
                '--include "*.bin" '
                '--exclude "test_*.csv" '
                '--exclude "test_*.lid" '
                '--include "*.txt" {}'
            ).format(_k, _s, _bin, m, _n, um, dr)

        # ---------------------------------------------------
        # once formatted the proper AWS sync command, run it
        # ---------------------------------------------------
        rv = sp.run(c, shell=True, stdout=sp.PIPE, stderr=sp.PIPE)
        if rv.stdout:
            lg.a(rv.stdout)
        if rv.returncode:
            lg.a("error: {}".format(rv.stderr))
        all_rv += rv.returncode

    # AWS S3 sync went OK
    _t = datetime.datetime.now()
    if all_rv == 0:
        _u(STATE_DDS_NOTIFY_CLOUD_OK)
        lg.a("success: cloud sync on {}".format(_t))
        _touch_s3_ts()
        # tell status DB for API purposes all went fine
        ddh_write_aws_sqs_ts('aws', 'ok')
        # AWS it's a separate process, can exit here
        sys.exit(0)

    # ERROR AWS S3 sync, check case bad enough for alarm
    ts = _get_s3_ts()
    delta = int(time.time()) - int(ts)
    if ts:
        if delta > 0:
            if delta > PERIOD_ALARM_AWS_S3:
                lg.a('error: too many bad S3, creating alarm SQS file')
                _touch_s3_ts()
                notify_error_sw_aws_s3()
            else:
                lg.a('warning: bad S3, but not critical yet')
        else:
            lg.a('error: negative S3 delta, fixing')
            _touch_s3_ts()
    else:
        # file does not even exist, probably first time ever
        lg.a('warning: bad S3, monitoring next ones')
        _touch_s3_ts()

    # something went wrong
    _u(STATE_DDS_NOTIFY_CLOUD_ERR)
    lg.a("error: cloud sync on {}, rv {}".format(_t, all_rv))
    ddh_write_aws_sqs_ts('aws', 'error')
    sys.exit(2)


def aws_serve():

    # check someone asked for AWS sync from GUI
    flag_gui = dds_get_aws_has_something_to_do_via_gui_flag_file()
    exists_flag_gui = os.path.exists(flag_gui)

    # nothing to do
    if not its_time_to("aws_s3_sync", PERIOD_AWS_S3_SECS) \
            and not exists_flag_gui:
        return

    # nothing to do, in fact, disabled
    if not dds_get_cfg_aws_en():
        lg.a("warning: aws_en is disabled")
        return

    # tell why we do AWS
    if os.path.exists(flag_gui):
        lg.a("debug: the aws_do_flag_gui is set")
        os.unlink(flag_gui)
    else:
        lg.a("it seems it's time for some AWS S3 syncing")

    # ---------------------------------------------------
    # nothing to AWS sync, number of files did not change
    # ---------------------------------------------------
    # todo ---> test pre and post comparison of number AWS files
    mon_ls = []
    for i in ('lid', 'lix', 'csv', 'cst', 'gps', 'bin'):
        mon_ls += glob.glob(f'{get_ddh_folder_path_dl_files()}/**/*.{i}')
    global past_n_files
    ff_ctt = (not exists_flag_gui) and len(mon_ls) == past_n_files
    past_n_files = len(mon_ls)
    if len(mon_ls) == 0:
        _u(STATE_DDS_NOTIFY_CLOUD_OK)
        lg.a('warning: AWS zero number of files, not syncing')
        return
    if ff_ctt:
        lg.a('warning: AWS same number of files, not syncing')
        return
    lg.a(f'debug: "dl_files" folder currently has {len(mon_ls)} files')

    # useful to remove past AWS bin zombie processes
    multiprocessing.active_children()

    # don't run if already doing so
    # which would be bad because means is taking too long
    if linux_is_process_running(AWS_S3_SYNC_PROC_NAME):
        s = "warning: seems last {} took a long time"
        lg.a(s.format(AWS_S3_SYNC_PROC_NAME))
        _u(STATE_DDS_NOTIFY_CLOUD_ERR)
        return

    # --------------------------------------------
    # run as a different process for smoother GUI
    # --------------------------------------------
    if dev:
        lg.a("debug: dev platform detected, AWS sync with --dryrun flag")
    p = Process(target=_aws_s3_sync_process)
    p.start()


# test
if __name__ == "__main__":
    aws_serve()
