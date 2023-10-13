#!/usr/bin/env python3
import datetime
import glob
import multiprocessing
import os
import subprocess as sp
import sys
import time
from multiprocessing import Process
import setproctitle

from dds.emolt import this_box_has_grouped_s3_uplink
from dds.sqs import sqs_msg_ddh_alarm_s3
from dds.timecache import its_time_to
from liu.linux import linux_is_process_running
from mat.utils import linux_is_rpi
from settings import ctx
from utils.ddh_shared import (
    send_ddh_udp_gui as _u,
    get_ddh_folder_path_dl_files,
    STATE_DDS_NOTIFY_CLOUD_LOGIN,
    STATE_DDS_NOTIFY_CLOUD_BUSY,
    STATE_DDS_NOTIFY_CLOUD_ERR,
    STATE_DDS_NOTIFY_CLOUD_OK,
    dds_get_aws_has_something_to_do_via_gui_flag_file, dds_get_json_vessel_name,
)
from utils.logs import lg_aws as lg


PATH_FILE_AWS_TS = get_ddh_folder_path_dl_files()
PERIOD_AWS_S3_SECS = 3600 * 6
PERIOD_ALARM_AWS_S3 = 86400 * 7
AWS_S3_SYNC_PROC_NAME = "dds_aws_sync"
dev = not linux_is_rpi()


def _get_aws_bin_path():
    # requires $ sudo pip install awscli
    return "aws"


def _touch_s3_ts():
    name = str(PATH_FILE_AWS_TS) + '/.ts_aws.txt'
    with open(name, 'w') as f:
        f.write(str(int(time.time())))


def _get_s3_ts():
    name = str(PATH_FILE_AWS_TS) + '/.ts_aws.txt'
    try:
        with open(name, 'r') as f:
            return f.readline()
    except FileNotFoundError:
        return


def _aws_s3_sync_process():

    # -----------------------------------------------------
    # sys.exit instead of return prevents zombie processes
    # -----------------------------------------------------
    setproctitle.setproctitle(AWS_S3_SYNC_PROC_NAME)
    fol_dl_files = get_ddh_folder_path_dl_files()
    _k = os.getenv("DDH_AWS_KEY_ID")
    _s = os.getenv("DDH_AWS_SECRET")
    _n = os.getenv("DDH_AWS_BUCKET")
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
        # um: dl_files/ddh#red_feet
        um = m.replace('dl_files/', '')
        c = (
            "AWS_ACCESS_KEY_ID={} AWS_SECRET_ACCESS_KEY={} "
            "{} s3 sync {} s3://{}/{} "
            '--exclude "*" '
            '--include "*.csv" '
            '--include "*.gps" '
            '--include "*.lid" '
            '--include "*.bin" '
            '--exclude "test_*.csv '
            '--exclude "test_*.lid '
            '--include "*.txt" {}'
        )
        c = c.format(_k, _s, _bin, m,
                     _n, um, dr)

        # mostly for CFA and emolt boxes
        if this_box_has_grouped_s3_uplink():
            v = dds_get_json_vessel_name()
            # v: "bailey's" --> BAYLEYS
            v = v.replace("'", "")
            v = v.replace(" ", "_")
            v = v.upper()
            # um: dl_files/ddh#red_feet
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
                '--exclude "test_*.csv '
                '--exclude "test_*.lid '
                '--include "*.txt" {}'
            )

            c = c.format(_k, _s, _bin, m,
                         _n, um, dr)

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
        sys.exit(0)

    # ERROR AWS S3 sync, check case bad enough for alarm
    ts = _get_s3_ts()
    delta = int(time.time()) - int(ts)
    if ts:
        if delta > 0:
            if delta > PERIOD_ALARM_AWS_S3:
                lg.a('error: too many bad S3, creating alarm')
                _touch_s3_ts()
                sqs_msg_ddh_alarm_s3()
            else:
                lg.a('warning: bad S3, but not critical yet')
        else:
            lg.a('error: negative S3 delta, fixing')
            _touch_s3_ts()
    else:
        # not even file since it is first time ever
        lg.a('warning: bad S3, monitoring next ones')
        _touch_s3_ts()

    # something went wrong
    _u(STATE_DDS_NOTIFY_CLOUD_ERR)
    lg.a("error: cloud sync on {}, rv {}".format(_t, all_rv))
    sys.exit(2)


def aws_serve():

    # check someone asked for AWS sync from GUI
    flag_gui = dds_get_aws_has_something_to_do_via_gui_flag_file()
    exists_flag_gui = os.path.exists(flag_gui)

    # nothing to do
    if not its_time_to("aws_s3_sync", PERIOD_AWS_S3_SECS) and not exists_flag_gui:
        return

    # explicitly don't do anything
    if not ctx.aws_en:
        lg.a("warning: ctx.aws_en set as False")
        return

    # tell why we do AWS
    if os.path.exists(flag_gui):
        lg.a("debug: aws_do_flag_gui is set")
        os.unlink(flag_gui)
    else:
        lg.a("period elapsed, time to do some AWS S3")

    # useful to remove zombie processes
    multiprocessing.active_children()

    # don't run if already doing so, but would be bad :(
    if linux_is_process_running(AWS_S3_SYNC_PROC_NAME):
        s = "warning: seems last {} took a long time"
        lg.a(s.format(AWS_S3_SYNC_PROC_NAME))
        _u(STATE_DDS_NOTIFY_CLOUD_ERR)
        return

    # run as a different process for smoother GUI
    if dev:
        lg.a("warning: dev platform detected, AWS sync with --dryrun flag")
    p = Process(target=_aws_s3_sync_process)
    p.start()


if __name__ == "__main__":
    aws_serve()
