#!/usr/bin/env python3

import datetime
import pathlib
import shutil
import setproctitle
from api.api_utils import (get_git_commit_mat_local,
                           get_ip_vpn, get_ip_wlan, get_ip_cell,
                           get_running, get_crontab_ddh, shell,
                           set_crontab,
                           get_git_commit_ddh_local,
                           get_ble_state, get_gps, get_logger_mac_reset_files,
                           get_versions,
                           api_get_full_ddh_config_file_path,
                           linux_app_write_pid_to_tmp, linux_is_rpi,
                           api_get_folder_path_root, ddt_get_folder_path_root,
                           get_uptime, get_crontab_api)
from utils.ddh_config import dds_get_cfg_vessel_name, dds_get_cfg_box_sn, dds_get_cfg_box_project
import uvicorn
from fastapi import FastAPI, UploadFile, File
import os
from fastapi.responses import FileResponse
import concurrent.futures


DDH_PORT_API = 8000
NAME_EXE_API = "main_api"
PID_FILE_API = "/tmp/{}.pid".format(NAME_EXE_API)


app = FastAPI()


def _get_ddh_folder_path_dl_files():
    d = api_get_folder_path_root()
    return f'{d}' + '/dl_files'


@app.get('/ping')
async def ep_ping():
    d = {
        "ping": "OK",
        "ip_vpn": get_ip_vpn(),
        "ip_wlan": get_ip_wlan(),
        "vessel": dds_get_cfg_vessel_name(),
        "last_gps": get_gps(),
        "is_rpi": linux_is_rpi(),
        "uptime": get_uptime()
    }
    return d


ep = 'upload_conf'


@app.post(f"/{ep}")
async def api_upload_conf(file: UploadFile = File(...)):
    if not file.filename == 'config.toml':
        return {ep: 'error_name'}

    # accept the upload and save it to /tmp folder
    uploaded_name = f'/tmp/{file.filename}'
    try:
        with open(uploaded_name, "wb") as buf:
            shutil.copyfileobj(file.file, buf)
    except (Exception, ):
        return {ep: 'error_uploading'}

    # overwrite DDH configuration only on DDH boxes
    if not linux_is_rpi():
        return {ep: 'no_install_not_Rpi'}

    p = api_get_full_ddh_config_file_path()
    rv = shell(f'cp {uploaded_name} {p}')
    if rv.returncode:
        return {ep: 'error_installing'}

    # response back
    return {ep: 'OK'}


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
        "last_gps": _th(get_gps),
        "uptime": _th(get_uptime),
        "ble_state": _th(get_ble_state),
        "boat_prj": _th(dds_get_cfg_box_project),
        "boat_sn": _th(dds_get_cfg_box_sn),
        "boat_name": _th(dds_get_cfg_vessel_name),
        "running": _th(get_running),
        "crontab_ddh": _th(get_crontab_ddh),
        "crontab_api": _th(get_crontab_api),
        "mac_reset_files": _th(get_logger_mac_reset_files),
        "versions": _th(get_versions),
        # "commit_mat": _th(get_git_commit_mat_local),
        # "commit_ddh": _th(get_git_commit_ddh_local),
    }
    return d


@app.get('/logs_get')
async def ep_logs_get():
    now = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    vn = dds_get_cfg_vessel_name().replace(' ', '')
    f = f'/tmp/logs_{vn}_{now}.zip'
    d = api_get_folder_path_root()
    # zip ONLY .log files
    c = f'cd {d}/logs && zip -r {f} *.log'
    rv = shell(c)
    if rv.returncode == 0:
        return FileResponse(path=f, filename=os.path.basename(f))


@app.get("/conf_get")
async def ep_conf_get():
    # prepare the zip file name
    vn = dds_get_cfg_vessel_name()
    vn = vn.replace(' ', '')

    # zip it, -o flag overwrites if already exists
    f = f'/tmp/conf_{vn}.zip'
    d = api_get_folder_path_root()
    c = f'cd {d}/settings && zip -o {f} config.toml'
    rv = shell(c)

    # send it as response
    if rv.returncode == 0:
        return FileResponse(path=f, filename=os.path.basename(f))


@app.get("/dl_files_get")
async def ep_dl_files_get():
    vn = dds_get_cfg_vessel_name()
    vn = vn.replace(' ', '')
    f = '/tmp/dl_files_{}.zip'.format(vn)

    # zip it, -o flag overwrites if already exists
    s = _get_ddh_folder_path_dl_files()
    c = f'cd {s} && zip -ro {f} *'
    rv = shell(c)

    # send it as response
    if rv.returncode == 0:
        return FileResponse(path=f, filename=os.path.basename(f))


def _ep_update(_ep, c):
    if not linux_is_rpi():
        return {ep: 'not RPi, not updating DDH'}
    rv = shell(c)
    with open('/tmp/ddr_update_log.txt', 'w') as f:
        f.write(f'rc {rv.returncode}')
        f.write(f'er {rv.stderr.decode()}')
        f.write(f'ou {rv.stdout.decode()}')
    return {_ep: 'OK' if rv.returncode == 0 else 'error'}


@app.get('/update_ddt')
async def ep_update_ddt():
    d = ddt_get_folder_path_root()
    return _ep_update('update_ddt', f'{d}/pop_ddt.sh')


@app.get('/update_ddh')
async def ep_update_ddh():
    d = ddt_get_folder_path_root()
    return _ep_update('update_ddh', f'{d}/pop_ddh.sh')


@app.get('/update_mat')
async def ep_update_mat():
    d = ddt_get_folder_path_root()
    return _ep_update('update_mat', f'{d}/pop_mat.sh')


@app.get('/kill_ddh')
async def ep_kill_ddh():
    d = dict()
    for i in ('main_ddh', 'main_ddh_controller',
              'main_dds', 'main_dds_controller'):
        rv = shell(f'killall {i}')
        s = rv.stderr.decode().replace('\n', '')
        if rv.returncode == 0:
            s = 'OK'
        if 'no process found' in s:
            s = 'N/A'
        # shorter name
        j = i.replace('main_', '')
        d[j] = s
    return d


@app.get('/kill_api')
async def ep_kill_api():
    shell('killall main_api')
    # does not matter, won't answer
    return {'kill_api': 'OK'}


@app.get("/cron_ena")
async def ep_crontab_enable():
    if not linux_is_rpi():
        return {'cron_ena': 'not RPi, not enabling crontab'}
    set_crontab(1)
    return {'cron_ena': get_crontab_ddh()}


@app.get("/cron_dis")
async def ep_crontab_disable():
    if not linux_is_rpi():
        return {'cron_dis': 'not RPi, not disabling crontab'}
    set_crontab(0)
    return {'cron_dis': get_crontab_ddh()}


def main_api():
    # docs at http://0.0.0.0/port/docs
    setproctitle.setproctitle(NAME_EXE_API)
    linux_app_write_pid_to_tmp(PID_FILE_API)
    uvicorn.run(app, host="0.0.0.0", port=DDH_PORT_API)


if __name__ == "__main__":
    main_api()
