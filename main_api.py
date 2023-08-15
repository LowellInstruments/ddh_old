#!/usr/bin/env python3

import datetime
import pathlib
import re
import shutil
import time
import setproctitle
from api.api_utils import get_git_commit_mat_local, \
    get_boat_sn, get_ip_vpn, get_ip_wlan, get_ip_cell, \
    get_running, get_crontab_ddh, shell, \
    set_crontab, \
    get_git_commit_ddh_local, \
    get_ble_state, get_gps, get_logger_mac_reset_files, get_versions
from liu.ddh_api_ep import EP_LOGS_GET, EP_PING, EP_INFO, EP_UPDATE_DDH, EP_UPDATE_MAT, EP_UPDATE_DDT, EP_KILL_DDH, \
    EP_KILL_API, EP_CRON_ENA, EP_CRON_DIS, EP_CONF_GET, LIST_CONF_FILES, EP_CONF_SET, EP_MAC_LOGGER_RESET, EP_UPDATE_LIU
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


# ---------------------------------------------------------------------
# to configure pycharm:
#     in "target to run" instead of "Script path" choose "Module name"
#     In Module name type uvicorn
#     In parameters app.main:app --reload --port 5000
# ---------------------------------------------------------------------


app = FastAPI()


@app.get('/' + EP_PING)
async def ep_ping():
    d = {
        EP_PING: "OK",
        "ip": get_ip_vpn(),
        "vessel": dds_get_json_vessel_name()
    }
    return d


@app.get('/' + EP_INFO)
async def api_get_info():
    d = {
        EP_INFO: "OK",
        "ip_vpn": get_ip_vpn(),
        "ip_wlan": get_ip_wlan(),
        "ip_cell": get_ip_cell(),
        "gps": get_gps(),
        "ble_state": get_ble_state(),
        "boat_sn": get_boat_sn(),
        "boat_name": dds_get_json_vessel_name(),
        "running": get_running(),
        "crontab": get_crontab_ddh(),
        "mac_reset_files": get_logger_mac_reset_files(),
        "versions": get_versions(),
        "commit_mat": get_git_commit_mat_local(),
        "commit_ddh": get_git_commit_ddh_local(),
    }
    return d


@app.get('/' + EP_LOGS_GET)
async def ep_logs_get():
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


@app.put("/" + EP_MAC_LOGGER_RESET + "/{mac}")
async def api_logger_reset_mac_set(mac: str):
    mac = mac.replace(':', '-')
    # security: check this is a MAC address and not a malformed path
    r1 = re.search("^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$", mac)
    if r1:
        path_file = 'api/{}.rst'.format(mac)
        pathlib.Path(path_file).touch()
        return {EP_MAC_LOGGER_RESET: "OK"}
    return {EP_MAC_LOGGER_RESET: "error"}


@app.get("/" + EP_CONF_GET)
async def ep_conf_get():
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


@app.post("/" + EP_CONF_SET)
async def api_conf_set(file: UploadFile = File(...)):
    if not file.filename.startswith('conf_'):
        return {EP_CONF_SET: 'error_name'}
    if not file.filename.endswith('.zip'):
        return {EP_CONF_SET: 'error_name'}

    # clean any remains from conf_get() method
    c = 'rm /tmp/conf_*.zip'
    shell(c)

    # accept the upload and save it to /tmp folder
    dst_zip = '/tmp/' + file.filename
    try:
        with open(dst_zip, "wb") as buf:
            shutil.copyfileobj(file.file, buf)
    except (Exception, ):
        return {EP_CONF_SET: 'error_saving'}

    # clean the /tmp folder where we will unzip
    dst_fol = dst_zip.replace('.zip', '')
    if os.path.exists(dst_fol):
        c = 'rm -rf {}'.format(dst_fol)
        rv = shell(c)
        if rv.returncode:
            return {EP_CONF_SET: 'error_deleting'}

    # unzip
    c = 'cd /tmp && unzip {}'.format(file.filename)
    rv = shell(c)
    if rv.returncode:
        return {EP_CONF_SET: 'error_unzipping'}

    # overwrite DDH configuration
    c = 'cp -r {}/* .'.format(dst_fol)
    rv = shell(c)
    if rv.returncode:
        return {EP_CONF_SET: 'error_installing'}

    # response back
    return {EP_CONF_SET: 'OK'}


async def _ep_update(ep, c):
    if not linux_is_rpi():
        return {ep: 'not RPi, not updating DDH'}
    rv = shell(c)
    a = 'OK' if rv.returncode == 0 else 'error'
    return {ep, a}


@app.get("/" + EP_UPDATE_DDT)
async def ep_update_ddt():
    return await _ep_update(EP_UPDATE_DDT, 'cd ../ddt && git pull')


@app.get("/" + EP_UPDATE_DDH)
async def ep_update_ddh():
    return await _ep_update(EP_UPDATE_DDH, 'cd scripts && ./pop_ddh.sh')


@app.get("/" + EP_UPDATE_MAT)
async def ep_update_mat():
    return await _ep_update(EP_UPDATE_MAT, 'cd scripts && ./pop_mat.sh')


@app.get("/" + EP_UPDATE_LIU)
async def ep_update_mat():
    return await _ep_update(EP_UPDATE_LIU, 'cd scripts && ./pop_liu.sh')


@app.get("/" + EP_KILL_DDH)
async def ep_kill_ddh():
    rv_h = shell("killall main_ddh")
    rv_s = shell("killall main_dds")
    ans_h = rv_h.stderr.decode().replace('\n', '')
    if rv_h.returncode == 0:
        ans_h = 'OK'
    ans_s = rv_s.stderr.decode().replace('\n', '')
    if rv_s.returncode == 0:
        ans_s = 'OK'
    return {EP_KILL_DDH: {'ddh': ans_h, 'dds': ans_s}}


@app.get("/" + EP_KILL_API)
async def ep_kill_api():
    shell('killall main_api_controller')
    shell('killall main_api')
    # does not matter, won't answer
    return {EP_KILL_API: 'OK'}


@app.get("/" + EP_CRON_ENA)
async def ep_crontab_enable():
    if not linux_is_rpi():
        return {EP_CRON_ENA: 'not RPi, not enabling crontab'}
    set_crontab(1)
    return {EP_CRON_ENA: get_crontab_ddh()}


@app.get("/" + EP_CRON_DIS)
async def ep_crontab_disable():
    if not linux_is_rpi():
        return {EP_CRON_DIS: 'not RPi, not disabling crontab'}
    set_crontab(0)
    return {EP_CRON_DIS: get_crontab_ddh()}


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
