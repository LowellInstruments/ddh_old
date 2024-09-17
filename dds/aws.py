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
from dds.net import ddh_get_internet_via
from dds.notifications import notify_error_sw_aws_s3
from dds.state import ddh_state
from dds.timecache import is_it_time_to
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
    dds_get_aws_has_something_to_do_via_gui_flag_file, ddh_get_db_status_file
)
from utils.logs import lg_aws as lg

g_fresh_boot = 1
PERIOD_AWS_S3_SECS = 3600 * 6
PERIOD_ALARM_AWS_S3 = 86400 * 7
AWS_S3_SYNC_PROC_NAME = "dds_aws_sync"
AWS_S3_CP_PROC_NAME = "dds_aws_cp"
dev = not linux_is_rpi()
past_n_files = 0


def _get_aws_bin_path():
    # apt install awscli
    # 2024 is 1.22.34
    return "aws"


def ddh_write_aws_sqs_ts(k, v):
    assert k in ('aws', 'sqs')
    # v: 'ok', 'error', 'unknown'
    assert type(v) is str

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


def ddh_get_aws_sqs_ts(k):
    assert k in ('aws', 'sqs')
    p = ddh_get_db_status_file()

    # load the file
    try:
        with open(p, 'r') as f:
            j = json.load(f)
            # {"aws": ["unknown", 1724246474], ... }
            return j[k][1]
    except (Exception, ):
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
        # _n: bkt-kaz
        # um: '/home/kaz/PycharmProjects/ddh/dl_files/ddh#joaquim_boat or <mac>'
        um = m.split('/')[-1]
        y = datetime.datetime.utcnow().year
        sy = str(y)[2:]
        if this_box_has_grouped_s3_uplink():
            lg.a(f'debug: AWS upload-sync as grouped mode for mac {um}')
            v = dds_get_cfg_vessel_name()
            # v: "bailey's" --> BAYLEYS
            v = v.replace("'", "")
            v = v.replace(" ", "_")
            v = v.upper()
            # um: we prepend grouped structure year and boat
            um = f"{str(y)}/{v}/{um}"
        else:
            lg.a(f'debug: AWS upload-sync as non-grouped mode for mac {um}')

        # build the AWS command
        c = (
            f"AWS_ACCESS_KEY_ID={_k} AWS_SECRET_ACCESS_KEY={_s} "
            f"{_bin} s3 sync {m} s3://{_n}/{um} "
            '--exclude "*" '
            # Moana filenames are unpredictable
            # MOANA_0113_173_240125092721.bin
            f'--include "*_*_*_{sy}*.bin" '
            f'--include "*_*_*_{sy}*.csv" '
            # Lowell's filenames
            # 3333333_low_20240521_101541.gps
            f'--include "*_*_{y}????_*.gps" '
            f'--include "*_*_{y}????_*.lid" '
            # 3333333_low_20240521_101541_DissolvedOxygen.csv
            f'--include "*_*_{y}????_*_*.csv" '
            f'--include "*_*_{y}????_*_*.cst" '
            # do not upload these
            '--exclude "test_*.csv" '
            '--exclude "test_*.lid" '
            # 2024-07-24T14:11:07Z#nameofboat_track
            f'--include "{y}-*.txt" '
            f'{dr}'
        )

        # ---------------------------------------------------
        # once formatted the proper AWS sync command, run it
        # ---------------------------------------------------
        rv = sp.run(c, shell=True, stdout=sp.PIPE, stderr=sp.PIPE)
        if rv.stdout:
            lg.a(rv.stdout)
        if rv.returncode:
            lg.a(f"error: {rv.stderr}")
        all_rv += rv.returncode

    # AWS S3 sync went OK
    _t = datetime.datetime.now()
    if all_rv == 0:
        _u(STATE_DDS_NOTIFY_CLOUD_OK)
        lg.a(f"success: cloud sync on {_t}")
        # tell status DB for API purposes all went fine
        ddh_write_aws_sqs_ts('aws', 'ok')

        # this AWS code is a separate process, we can exit here
        sys.exit(0)

    # ERROR AWS S3 sync, check case bad enough for alarm
    ts = ddh_get_aws_sqs_ts('aws')
    delta = int(time.time()) - int(ts)
    if ts:
        if delta > 0:
            if delta > PERIOD_ALARM_AWS_S3:
                lg.a('error: too many bad S3, creating alarm SQS file')
                notify_error_sw_aws_s3()
            else:
                lg.a('warning: bad S3, but not critical yet')
        else:
            lg.a('error: negative S3 delta, fixing')
    else:
        # file does not even exist, probably first time ever
        lg.a('warning: bad S3, monitoring next ones')

    # something went wrong
    _u(STATE_DDS_NOTIFY_CLOUD_ERR)
    lg.a(f"error: cloud sync on {_t}, rv {all_rv}")
    ddh_write_aws_sqs_ts('aws', 'error')
    sys.exit(2)


def aws_serve():

    # check someone asked for AWS sync from GUI
    flag_gui = dds_get_aws_has_something_to_do_via_gui_flag_file()
    exists_flag_gui = os.path.exists(flag_gui)

    if ddh_state.get_downloading_ble():
        lg.a('warning: not doing AWS sync while downloading BLE')
        return

    # nothing to do
    if not is_it_time_to("aws_s3_sync", PERIOD_AWS_S3_SECS) \
            and not exists_flag_gui:
        return

    # nothing to do, in fact, disabled
    if not dds_get_cfg_aws_en():
        lg.a("warning: aws_en is disabled")
        return

    if ddh_get_internet_via() == 'none':
        lg.a('error: no AWS sync attempt because no internet access')
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


def _aws_s3_cp_process(d):

    # sys.exit() instead of return prevents zombie processes
    setproctitle.setproctitle(AWS_S3_CP_PROC_NAME)
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

    for f in d:
        # _n: bkt-kaz
        # f: '/home/kaz/PycharmProjects/ddh/dl_files/d0-2e-ab-d9-30-66/2222222_TST_20240904_143008.gps
        um = f.split('/')[-2]
        f_bn = os.path.basename(f)
        y = datetime.datetime.utcnow().year
        if this_box_has_grouped_s3_uplink():
            lg.a(f'debug: AWS upload-cp as grouped mode for mac {um}')
            v = dds_get_cfg_vessel_name()
            # v: "bailey's" --> BAYLEYS
            v = v.replace("'", "")
            v = v.replace(" ", "_")
            v = v.upper()
            # um: we prepend grouped structure year and boat
            um = f"{str(y)}/{v}/{um}"
        else:
            lg.a(f'debug: AWS upload-cp as non-grouped mode for mac {um}')

        # build the AWS command
        c = (
            f"AWS_ACCESS_KEY_ID={_k} AWS_SECRET_ACCESS_KEY={_s} "
            f"{_bin} s3 cp {f} s3://{_n}/{um}/{f_bn} {dr}"
        )

        # ---------------------------------------------------
        # once formatted the proper AWS cp command, run it
        # ---------------------------------------------------
        rv = sp.run(c, shell=True, stdout=sp.PIPE, stderr=sp.PIPE)
        if rv.stdout:
            lg.a(rv.stdout)
        if rv.returncode:
            lg.a(f"error: {rv.stderr}")
            sys.exit(2)
        else:
            _t = datetime.datetime.now()
            lg.a(f"success: cloud cp on {_t}, file {f}")

    # this AWS cp is a separate process, we can exit here
    sys.exit(0)


def aws_cp(d):

    # d: aws_cp_d ['/home/.../dl_files/<mac>/2222222_TST_20240904_143008.gps', ...]
    if not d:
        lg.a("error: called aws_cp with empty list")
        return

    # nothing to do, in fact, disabled
    if not dds_get_cfg_aws_en():
        lg.a("warning: aws_en is disabled, will not cp")
        return

    if ddh_get_internet_via() == 'none':
        lg.a('error: no AWS cp attempt because no internet access')
        return

    lg.a("it seems we can attempt an AWS S3 copying")

    # gets rid of zombie processes
    multiprocessing.active_children()

    # don't run if already doing so
    if linux_is_process_running(AWS_S3_SYNC_PROC_NAME):
        lg.a('warning: not running AWS cp, because AWS sync in progress')
        return
    if linux_is_process_running(AWS_S3_CP_PROC_NAME):
        lg.a('warning: not running AWS cp, because last AWS cp took long time')
        return

    # run as a different process for smoother GUI
    if dev:
        lg.a("debug: dev platform detected, AWS cp with --dryrun flag")
    p = Process(target=_aws_s3_cp_process, args=(d, ))
    p.start()


# test
if __name__ == "__main__":
    _d = [
        '/home/kaz/PycharmProjects/ddh/dl_files/d0-2e-ab-d9-30-66/2222222_TST_20240904_143008.gps',
        '/home/kaz/PycharmProjects/ddh/dl_files/d0-2e-ab-d9-30-66/2222222_TST_20240904_143008.lid']
    aws_cp(_d)
