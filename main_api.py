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
    get_ble_state, get_gps, get_logger_mac_reset_files, get_versions, get_boat_project
from dds.rbl import rbl_find_usb_port
from mat.linux import linux_app_write_pid_to_tmp, linux_is_process_running
from mat.utils import linux_is_rpi
from utils.ddh_config import dds_get_json_vessel_name
from utils.ddh_shared import NAME_EXE_API_CONTROLLER, \
    PID_FILE_API_CONTROLLER, \
    NAME_EXE_API, PID_FILE_API, get_ddh_folder_path_dl_files
from utils.logs import (
    lg_api as lg,
)
from multiprocessing import Process
import uvicorn
from fastapi import FastAPI, UploadFile, File
import os
from fastapi.responses import FileResponse
import concurrent.futures


# ---------------------------------------------------------------------
# to configure pycharm:
#     in "target to run" instead of "Script path" choose "Module name"
#     In Module name type uvicorn
#     In parameters app.main:app --reload --port 5000
# ---------------------------------------------------------------------


LIST_CONF_FILES = {
    'settings/ddh.json',
    'settings/ctx.py',
    'run_dds.sh',
    'settings/_li_all_macs_to_sn.yml',
    '/etc/crontab'
}


app = FastAPI()


@app.get('/ping')
async def ep_ping():
    d = {
        'ping': "OK",
        "ip_vpn": get_ip_vpn(),
        "ip_wlan": get_ip_wlan(),
        "vessel": dds_get_json_vessel_name()
    }
    return d


@app.get('/info')
async def api_get_info():
    def _th(cb):
        # src: stackoverflow 6893968
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(cb)
            return future.result()

    d = {
        'info': "OK",
        "ip_vpn": _th(get_ip_vpn),
        "ip_wlan": _th(get_ip_wlan),
        "ip_cell": _th(get_ip_cell),
        "gps": _th(get_gps),
        "rockblocks": _th(rbl_find_usb_port),
        "ble_state": _th(get_ble_state),
        "boat_prj": _th(get_boat_project),
        "boat_sn": _th(get_boat_sn),
        "boat_name": _th(dds_get_json_vessel_name),
        "running": _th(get_running),
        "crontab": _th(get_crontab_ddh),
        "mac_reset_files": _th(get_logger_mac_reset_files),
        "versions": _th(get_versions),
        "commit_mat": _th(get_git_commit_mat_local),
        "commit_ddh": _th(get_git_commit_ddh_local),
    }
    return d


@app.get('/logs_get')
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


@app.put("/mac_logger_reset/{mac}")
async def api_logger_reset_mac_set(mac: str):
    mac = mac.replace(':', '-')
    # security: check this is a MAC address and not a malformed path
    r1 = re.search("^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$", mac)
    if r1:
        path_file = 'api/{}.rst'.format(mac)
        pathlib.Path(path_file).touch()
        return {'mac_logger_reset': "OK"}
    return {'mac_logger_reset': "error"}


@app.get("/conf_get")
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


@app.get("/dl_files_get")
async def ep_dl_files_get():
    vn = dds_get_json_vessel_name()
    vn = vn.replace(' ', '')
    file_name = 'dl_files_{}.zip'.format(vn)

    # zip it, -o flag overwrites if already exists
    s = get_ddh_folder_path_dl_files()
    print('pwd', os.getcwd())
    print('getting files from', s)
    p = '/tmp/' + file_name
    c = 'zip -ro {} {}'.format(p, s)
    rv = shell(c)

    # send it as response
    if rv.returncode == 0:
        return FileResponse(path=p, filename=file_name)


@app.post("/conf_set")
async def api_conf_set(file: UploadFile = File(...)):
    if not file.filename.startswith('conf_'):
        return {'conf_set': 'error_name'}
    if not file.filename.endswith('.zip'):
        return {'conf_set': 'error_name'}

    # clean any remains from conf_get() method
    c = 'rm /tmp/conf_*.zip'
    shell(c)

    # accept the upload and save it to /tmp folder
    dst_zip = '/tmp/' + file.filename
    try:
        with open(dst_zip, "wb") as buf:
            shutil.copyfileobj(file.file, buf)
    except (Exception, ):
        return {'conf_set': 'error_saving'}

    # clean the /tmp folder where we will unzip
    dst_fol = dst_zip.replace('.zip', '')
    if os.path.exists(dst_fol):
        c = 'rm -rf {}'.format(dst_fol)
        rv = shell(c)
        if rv.returncode:
            return {'conf_set': 'error_deleting'}

    # unzip
    c = 'cd /tmp && unzip {}'.format(file.filename)
    rv = shell(c)
    if rv.returncode:
        return {'conf_set': 'error_unzipping'}

    # overwrite DDH configuration
    c = 'cp -r {}/* .'.format(dst_fol)
    rv = shell(c)
    if rv.returncode:
        return {'conf_set': 'error_installing'}

    # response back
    return {'conf_set': 'OK'}


def _ep_update(ep, c):
    if not linux_is_rpi():
        return {ep: 'not RPi, not updating DDH'}
    rv = shell(c)
    a = 'OK' if rv.returncode == 0 else 'error'
    return {ep: a}


@app.get("/" + 'update_ddt')
async def ep_update_ddt():
    return _ep_update('update_ddt', 'cd ../ddt && git pull')


@app.get("/" + 'update_ddh')
async def ep_update_ddh():
    return _ep_update('update_ddh', 'cd scripts && ./pop_ddh.sh')


@app.get("/" + 'update_mat')
async def ep_update_mat():
    return _ep_update('update_mat', 'cd scripts && ./pop_mat.sh')


@app.get("/" + 'update_liu')
async def ep_update_mat():
    return _ep_update('update_liu', 'cd scripts && ./pop_liu.sh')


@app.get("/" + 'kill_ddh')
async def ep_kill_ddh():
    rv_h = shell("killall main_ddh")
    rv_s = shell("killall main_dds")
    ans_h = rv_h.stderr.decode().replace('\n', '')
    if rv_h.returncode == 0:
        ans_h = 'OK'
    ans_s = rv_s.stderr.decode().replace('\n', '')
    if rv_s.returncode == 0:
        ans_s = 'OK'
    return {'kill_ddh': {'ddh': ans_h, 'dds': ans_s}}


@app.get("/" + 'kill_api')
async def ep_kill_api():
    shell('killall main_api_controller')
    shell('killall main_api')
    # does not matter, won't answer
    return {'kill_api': 'OK'}


@app.get("/" + 'cron_ena')
async def ep_crontab_enable():
    if not linux_is_rpi():
        return {'cron_ena': 'not RPi, not enabling crontab'}
    set_crontab(1)
    return {'cron_ena': get_crontab_ddh()}


@app.get("/" + 'cron_dis')
async def ep_crontab_disable():
    if not linux_is_rpi():
        return {'cron_dis': 'not RPi, not disabling crontab'}
    set_crontab(0)
    return {'cron_dis': get_crontab_ddh()}


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
