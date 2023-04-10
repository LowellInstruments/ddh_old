#!/usr/bin/env python3
import datetime
import multiprocessing
import os
import subprocess as sp
import sys
from multiprocessing import Process
import setproctitle
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
    dds_get_aws_has_something_to_do_via_gui_flag_file,
)
from utils.logs import lg_aws as lg


PERIOD_AWS_S3_SECS = 3600 * 6
AWS_S3_SYNC_PROC_NAME = "dds_aws_sync"
dev = not linux_is_rpi()


def _get_aws_bin_path():
    return "aws"


def _aws_s3_sync_process():

    # -----------------------------------------------------
    # sys.exit instead of return prevents zombie processes
    # -----------------------------------------------------
    setproctitle.setproctitle(AWS_S3_SYNC_PROC_NAME)
    fol = get_ddh_folder_path_dl_files()
    _k = os.getenv("DDH_AWS_KEY_ID")
    _s = os.getenv("DDH_AWS_SECRET")
    _n = os.getenv("DDH_AWS_BUCKET")
    if _k is None or _s is None or _n is None:
        lg.a("warning: missing credentials")
        _u(STATE_DDS_NOTIFY_CLOUD_LOGIN)
        sys.exit(1)

    if not _n.startswith("bkt-"):
        _n = "bkt-" + _n

    # ------------------------------
    # run it! we use aws-cli binary
    # ------------------------------
    _u(STATE_DDS_NOTIFY_CLOUD_BUSY)
    _bin = _get_aws_bin_path()
    dr = "--dryrun" if dev else ""
    c = (
        "AWS_ACCESS_KEY_ID={} AWS_SECRET_ACCESS_KEY={} "
        "{} s3 sync {} s3://{} "
        '--exclude "*" '
        '--include "*.csv" '
        '--include "*.gps" '
        '--include "*.lid" '
        '--include "*.bin" '
        '--include "*.txt" {}'
    )
    c = c.format(_k, _s, _bin, fol, _n, dr)
    rv = sp.run(c, shell=True, stdout=sp.PIPE, stderr=sp.PIPE)

    # indicate result
    _t = datetime.datetime.now()
    if rv.returncode == 0:
        _u(STATE_DDS_NOTIFY_CLOUD_OK)
        lg.a("success: cloud sync on {}".format(_t))
        if rv.stdout:
            lg.a(rv.stdout)
        sys.exit(0)

    # something went wrong
    _u(STATE_DDS_NOTIFY_CLOUD_ERR)
    lg.a("error: cloud sync on {}, rv {}".format(_t, rv.returncode))
    lg.a("error: {}".format(rv.stderr))
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
