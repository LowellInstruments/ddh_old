#!/usr/bin/env python3


import datetime
import glob
import json
import pathlib
import re
import shutil
import time
import setproctitle
from api.api_utils import get_git_commit_mat_local, \
    get_boat_sn, get_ip_vpn, get_ip_wlan, get_ip_cell, \
    get_running, LIST_CONF_FILES, get_crontab, shell, \
    set_crontab, get_git_commit_mat_remote, \
    get_git_commit_ddh_local, get_git_commit_ddh_remote, get_git_commit_ddt_local, get_git_commit_ddt_remote, \
    get_ble_state
from liu.linux import linux_app_write_pid_to_tmp, linux_is_process_running
from mat.utils import linux_is_rpi
from utils.ddh_shared import NAME_EXE_API_CONTROLLER, \
    PID_FILE_API_CONTROLLER, \
    dds_get_json_vessel_name, NAME_EXE_API, PID_FILE_API
from utils.logs import (
    lg_api as lg,
)
from multiprocessing import Process
import uvicorn
from fastapi import FastAPI, UploadFile, File
import os
from fastapi.responses import FileResponse
import inspect


# ---------------------------------------------------------------------
# to configure pycharm:
#     in "target to run" instead of "Script path" choose "Module name"
#     In Module name type uvicorn
#     In parameters app.main:app --reload --port 5000
# ---------------------------------------------------------------------


app = FastAPI()


@app.get("/info")
async def api_get_info():
    fxn = str(inspect.currentframe().f_code.co_name)
    d = {
        "ip_vpn": get_ip_vpn(),
        "ip_wlan": get_ip_wlan(),
        "ip_cell": get_ip_cell(),
        "crontab": get_crontab(),
        "boat_sn": get_boat_sn(),
        "boat_name": dds_get_json_vessel_name(),
        "commit_mat": get_git_commit_mat_local(),
        "commit_ddh": get_git_commit_ddh_local(),
        "running": get_running(),
    }
    return {fxn: d}


@app.get("/logs")
async def api_get_logs():
    now = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    vn = dds_get_json_vessel_name()
    vn = vn.replace(' ', '')
    file_name = 'logs_{}_{}.zip'.format(vn, now)
    # zip ONLY .log files
    c = 'zip -r {} logs/*.log'.format(file_name)
    rv = shell(c)
    if rv.returncode == 0:
        c = 'mv {} logs/'.format(file_name)
        rv = shell(c)
        if rv.returncode == 0:
            p = 'logs/' + file_name
            fr = FileResponse(path=p, filename=file_name)
            return fr


@app.get("/reset")
async def api_logger_reset_mac_get_all():
    fxn = str(inspect.currentframe().f_code.co_name)
    ff = glob.glob('api/*.rst')
    return {fxn: ff}


@app.put("/reset/{mac}")
async def api_logger_reset_mac_set(mac: str):
    fxn = str(inspect.currentframe().f_code.co_name)
    mac = mac.replace(':', '-')
    # security: check this is a MAC address and not a malformed path
    r1 = re.search("^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$", mac)
    if r1:
        path_file = 'api/{}.rst'.format(mac)
        pathlib.Path(path_file).touch()
        return {fxn: True}
    return {fxn: False}


@app.get("/files/conf_get")
async def api_conf_get():
    # prepare the zip file name
    s = ' '.join([f for f in LIST_CONF_FILES])
    vn = dds_get_json_vessel_name()
    vn = vn.replace(' ', '')
    file_name = 'conf_{}.zip'.format(vn)

    # zip it, -o flag overwrites if already exists
    p = '/tmp/' + file_name
    c = 'zip -o {} {}'.format(p, s)
    rv = shell(c)

    # send it as response
    if rv.returncode == 0:
        return FileResponse(path=p, filename=file_name)


@app.post("/files/conf_set")
async def api_conf_set(file: UploadFile = File(...)):
    fxn = str(inspect.currentframe().f_code.co_name)
    if not file.filename.startswith('conf_'):
        return {fxn: 'error_name'}
    if not file.filename.endswith('.zip'):
        return {fxn: 'error_name'}

    # clean any remains from conf_get() method
    c = 'rm /tmp/conf_*.zip'
    shell(c)

    # accept the upload and save it to /tmp folder
    dst_zip = '/tmp/' + file.filename
    try:
        with open(dst_zip, "wb") as buf:
            shutil.copyfileobj(file.file, buf)
    except (Exception, ):
        return {fxn: 'error_saving'}

    # clean the /tmp folder where we will unzip
    dst_fol = dst_zip.replace('.zip', '')
    if os.path.exists(dst_fol):
        c = 'rm -rf {}'.format(dst_fol)
        rv = shell(c)
        if rv.returncode:
            return {fxn: 'error_deleting'}

    # unzip
    c = 'cd /tmp && unzip {}'.format(file.filename)
    rv = shell(c)
    if rv.returncode:
        return {fxn: 'error_unzipping'}

    # overwrite DDH configuration
    c = 'cp -r {}/* .'.format(dst_fol)
    rv = shell(c)
    if rv.returncode:
        return {fxn: 'error_installing'}

    # response back
    fxn = str(inspect.currentframe().f_code.co_name)
    return {fxn: 'OK'}


@app.get("/versions")
async def api_versions():
    fxn = str(inspect.currentframe().f_code.co_name)
    v_mat_l = get_git_commit_mat_local()
    v_mat_r = get_git_commit_mat_remote()
    v_ddh_l = get_git_commit_ddh_local()
    v_ddh_r = get_git_commit_ddh_remote()
    v_ddt_l = get_git_commit_ddt_local()
    v_ddt_r = get_git_commit_ddt_remote()
    need_mat_update = v_mat_l != v_mat_r
    need_ddh_update = v_ddh_l != v_ddh_r
    need_ddt_update = v_ddt_l != v_ddt_r
    need_mat_update = 'yes' if need_mat_update else 'no'
    need_ddh_update = 'yes' if need_ddh_update else 'no'
    need_ddt_update = 'yes' if need_ddt_update else 'no'
    return {fxn: {'need_mat_update': need_mat_update,
                  'need_ddh_update': need_ddh_update,
                  'need_ddt_update': need_ddt_update}}


@app.get("/ping")
async def api_ping():
    fxn = str(inspect.currentframe().f_code.co_name)
    return {fxn: "pong",
            "ip": get_ip_vpn(),
            "vessel": dds_get_json_vessel_name()}


@app.get("/gps")
async def api_gps():
    fxn = str(inspect.currentframe().f_code.co_name)
    g = ''
    try:
        with open('/tmp/gps_last.json', 'r') as f:
            g = json.load(f)
    except (Exception, ):
        pass
    return {fxn: g}


@app.get("/ble_state")
async def api_ble_state():
    fxn = str(inspect.currentframe().f_code.co_name)
    return {fxn: get_ble_state()}


@app.get("/update_ddt")
async def api_update_ddt():
    fxn = str(inspect.currentframe().f_code.co_name)
    if not linux_is_rpi():
        return {fxn: 'not RPi, not updating DDH'}
    c = 'cd ../ddt && git pull'
    rv = shell(c)
    a = 'OK' if rv.returncode == 0 else 'error'
    return {
        fxn: a,
        "ddt_commit": get_git_commit_ddt_local()
    }


@app.get("/update_ddh")
async def update_ddh():
    fxn = str(inspect.currentframe().f_code.co_name)
    if not linux_is_rpi():
        return {fxn: 'not RPi, not updating DDH'}
    c = 'cd scripts && ./pop_ddh.sh'
    rv = shell(c)
    a = 'OK' if rv.returncode == 0 else 'error'
    return {
        fxn: a,
        "ddh_commit": get_git_commit_ddh_local()
    }


@app.get("/update_mat")
async def update_mat():
    fxn = str(inspect.currentframe().f_code.co_name)
    if not linux_is_rpi():
        return {fxn: 'not RPi, not updating mat'}
    c = 'cd scripts && ./pop_mat.sh'
    rv = shell(c)
    a = 'OK' if rv.returncode == 0 else 'error'
    return {
        fxn: a,
        "ddh_commit": get_git_commit_mat_local()
    }


@app.get("/kill_ddh")
async def api_kill_ddh():
    fxn = str(inspect.currentframe().f_code.co_name)
    rv_h = shell("killall main_ddh")
    rv_s = shell("killall main_dds")
    ans_h = rv_h.stderr.decode().replace('\n', '')
    if rv_h.returncode == 0:
        ans_h = 'OK'
    ans_s = rv_s.stderr.decode().replace('\n', '')
    if rv_s.returncode == 0:
        ans_s = 'OK'
    return {fxn: {'ddh': ans_h, 'dds': ans_s}}


@app.get("/kill_api")
async def api_kill_api():
    fxn = str(inspect.currentframe().f_code.co_name)
    shell("killall main_api_controller")
    shell("killall main_api")
    # ends here, crontab may relaunch us
    a = 'we_are_killing_ourselves_no_answer'
    return {fxn: a}


@app.get("/crontab_get")
async def api_crontab_get():
    fxn = str(inspect.currentframe().f_code.co_name)
    return {fxn: get_crontab()}


@app.get("/crontab_enable")
async def api_crontab_enable():
    fxn = str(inspect.currentframe().f_code.co_name)
    if not linux_is_rpi():
        return {fxn: 'not RPi, not enabling crontab'}
    set_crontab(1)
    return {fxn: get_crontab()}


@app.get("/crontab_disable")
async def api_crontab_disable():
    fxn = str(inspect.currentframe().f_code.co_name)
    if not linux_is_rpi():
        return {fxn: 'not RPi, not disabling crontab'}
    set_crontab(0)
    return {fxn: get_crontab()}


def main_api():
    # docs at http://0.0.0.0/port/docs
    setproctitle.setproctitle(NAME_EXE_API)
    linux_app_write_pid_to_tmp(PID_FILE_API)
    uvicorn.run(app, host="0.0.0.0", port=8000)


def controller_main_api():
    s = NAME_EXE_API_CONTROLLER
    p = PID_FILE_API_CONTROLLER
    setproctitle.setproctitle(s)
    linux_app_write_pid_to_tmp(p)
    lg.a("=== {} started ===".format(s))

    while 1:
        # the GUI KILLs this process when desired
        lg.a("=== {} launching child ===".format(s))
        p = Process(target=main_api)
        p.start()
        p.join()
        lg.a("=== {} waits child ===".format(s))
        time.sleep(5)


if __name__ == "__main__":

    if not linux_is_process_running(NAME_EXE_API_CONTROLLER):
        controller_main_api()
    else:
        e = "not launching {}, already running at python level"
        print(e.format(NAME_EXE_API_CONTROLLER))
