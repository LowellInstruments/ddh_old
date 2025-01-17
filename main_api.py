#!/usr/bin/env python3

import datetime
import glob
import pathlib
import shutil
import sys
import time
from multiprocessing import Process
import setproctitle
from api.api_utils import (
    api_get_ip_vpn,
    api_get_ip_wlan,
    api_get_ip_cell,
    api_get_running_ddh_dds,
    api_get_crontab_ddh,
    _sh,
    api_set_crontab,
    api_get_ble_state, api_get_gps,
    api_get_logger_mac_reset_files,
    api_get_commits,
    api_get_full_ddh_config_file_path,
    api_linux_is_rpi,
    api_get_folder_path_root,
    api_ddt_get_folder_path_root,
    api_get_uptime,
    api_get_crontab_api,
    api_read_aws_sqs_ts,
    api_get_timezone,
    CTT_API_OK,
    CTT_API_ER,
    api_get_uptime_secs,
    api_ddh_get_folder_dl_files,
    api_get_ddh_folder_path_macs_black,
    api_get_ddh_sw_version,
    api_get_utc_epoch,
    api_get_api_version,
    api_get_ble_iface,
    get_files_from_server,
    api_get_gps_iface,
    api_get_fw_cell_version,
    api_get_wlan_mbps,
    api_get_internet_via,
    api_get_kernel,
    api_send_email_crash,
    api_linux_is_process_running,
    api_get_disk_capacity, api_ddh_side_button_2
)
from ddh.db.db_his import DbHis
from utils.ddh_config import (
    dds_get_cfg_vessel_name,
    dds_get_cfg_box_sn,
    dds_get_cfg_box_project,
    dds_get_cfg_monitored_pairs
)
import uvicorn
from fastapi import (
    FastAPI,
    UploadFile,
    File,
    HTTPException
)
import os
from fastapi.responses import FileResponse
import concurrent.futures
import subprocess as sp
from utils.flag_paths import (
    LI_FILE_ICCID,
    TMP_PATH_DDH_APP_OVERRIDE,
    TMP_PATH_DDH_GOT_UPDATE
)


# instead, the DDN port is 9000 & 9001
DDH_PORT_API = 8000
DDN_API_PROVISIONING_PORT = 9001
DDN_API_PROVISIONING_IP = '10.5.0.1'
# do NOT remove this from here
NAME_EXE_API = "main_api"
NAME_EXE_API_CONTROLLER = NAME_EXE_API + "_controller"


app = FastAPI()

g_ts_last_email_api_crash = 0


def _p(s):
    print(s)


@app.get('/ping')
async def ep_ping():
    d = {
        "ping": CTT_API_OK,
        "ip_vpn": api_get_ip_vpn(),
        "ip_wlan": api_get_ip_wlan(),
        "boat_name": dds_get_cfg_vessel_name(),
        "last_gps": api_get_gps(),
        "is_rpi": api_linux_is_rpi(),
        "uptime": api_get_uptime()
    }
    return d


@app.get('/monitored_macs')
async def ep_monitored_macs():
    d = {
        "monitored_macs": dds_get_cfg_monitored_pairs(),
    }
    return d


@app.get('/history')
async def ep_history():
    # p: path relative to this current file
    p = 'ddh/db/db_his.json'
    db = DbHis(p)
    r = db.get_all()
    try:
        return {"history": CTT_API_OK, "entries": r}
    except (Exception, ):
        return {"history": CTT_API_ER, "entries": {}}


ep = 'upload_conf'


@app.post(f"/{ep}")
async def api_upload_conf(file: UploadFile = File(...)):
    if not file.filename == 'config.toml':
        return {ep: f'{CTT_API_ER}_filename'}

    # accept the upload and save it to /tmp folder
    uploaded_name = f'/tmp/{file.filename}'
    try:
        with open(uploaded_name, "wb") as buf:
            shutil.copyfileobj(file.file, buf)
    except (Exception, ):
        return {ep: f'{CTT_API_ER}_file_uploading'}

    # overwrite DDH configuration only on DDH boxes
    if not api_linux_is_rpi():
        return {ep: 'no_install_not_Rpi'}

    p = api_get_full_ddh_config_file_path()
    rv = _sh(f'cp {uploaded_name} {p}')
    if rv.returncode:
        return {ep: f'{CTT_API_ER}_file_install'}

    # response back
    return {ep: CTT_API_OK}


@app.get('/sim')
async def api_get_iccid():
    if not os.path.exists(LI_FILE_ICCID):
        # not even Quectel shield detected
        return {'iccid': None}
    try:
        with open(LI_FILE_ICCID, 'r') as f:
            ll = f.readlines()
        for li in ll:
            if li.startswith('+QCCID: '):
                s = li
                s = s.replace('^M', '')
                s = s.replace('\n', '')
                s = s.split()[1]
                return {'iccid': s}
        # file there but empty, such as no SIM case
        return {'iccid': None}
    except (Exception, ) as ex:
        return {'iccid': str(ex)}


@app.get('/info')
async def api_get_info():
    def _th(cb):
        # src: stackoverflow 6893968
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(cb)
            return future.result()

    d = {
        'info': CTT_API_OK,
        "ip_vpn": _th(api_get_ip_vpn),
        "ip_wlan": _th(api_get_ip_wlan),
        "ip_cell": _th(api_get_ip_cell),
        "wlan_mbps": _th(api_get_wlan_mbps),
        "internet_via": _th(api_get_internet_via),
        "last_gps": _th(api_get_gps),
        "uptime": _th(api_get_uptime),
        "uptime_secs": _th(api_get_uptime_secs),
        "ble_state": _th(api_get_ble_state),
        "ble_iface_used": _th(api_get_ble_iface),
        "gps_iface_used": _th(api_get_gps_iface),
        "disk_capacity": _th(api_get_disk_capacity),
        "aws_sqs_state": _th(api_read_aws_sqs_ts),
        "boat_prj": _th(dds_get_cfg_box_project),
        "boat_sn": _th(dds_get_cfg_box_sn),
        "boat_name": _th(dds_get_cfg_vessel_name),
        "running": _th(api_get_running_ddh_dds),
        "crontab_ddh": _th(api_get_crontab_ddh),
        "crontab_api": _th(api_get_crontab_api),
        "mac_reset_files": _th(api_get_logger_mac_reset_files),
        "versions": _th(api_get_commits),
        "utc_time": _th(api_get_utc_epoch),
        "time_zone": _th(api_get_timezone),
        "ddh_version": _th(api_get_ddh_sw_version),
        "api_version": _th(api_get_api_version),
        "cell_fw_ver": _th(api_get_fw_cell_version),
        "kernel": _th(api_get_kernel),
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
    c = f'rm {f}; cd {d}/logs && zip -r {f} *.log'
    rv = _sh(c)
    if rv.returncode == 0:
        return FileResponse(path=f, filename=os.path.basename(f))


@app.get("/dl_files_get")
async def ep_dl_files_get():
    vn = dds_get_cfg_vessel_name()
    vn = vn.replace(' ', '')
    f = f'/tmp/dl_files_{vn}.zip'

    # zip it, -o flag overwrites if already exists
    s = api_ddh_get_folder_dl_files()
    c = f'rm {f}; cd {s} && zip -r {f} *'
    rv = _sh(c)

    # send it as response
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
    c = f'rm {f}; cd {d}/settings && zip -o {f} config.toml'
    rv = _sh(c)

    # send it as response
    if rv.returncode == 0:
        return FileResponse(path=f, filename=os.path.basename(f))


def _ep_update(_ep, c):
    if not api_linux_is_rpi():
        return {ep: 'not RPi, not updating DDH'}
    rv = _sh(c)
    with open('/tmp/ddr_update_log.txt', 'w') as f:
        f.write(f'rc {rv.returncode}')
        f.write(f'er {rv.stderr.decode()}')
        f.write(f'ou {rv.stdout.decode()}')
    return {_ep: CTT_API_OK if rv.returncode == 0 else CTT_API_ER}


@app.get('/update_ddt')
async def ep_update_ddt():
    d = api_ddt_get_folder_path_root()
    return _ep_update('update_ddt', f'{d}/pop_ddt.sh')


@app.get('/update_ddh')
async def ep_update_ddh():
    d = api_ddt_get_folder_path_root()
    rv = _ep_update('update_ddh', f'{d}/pop_ddh.sh')
    if rv['update_ddh'] == CTT_API_OK:
        f = TMP_PATH_DDH_GOT_UPDATE
        pathlib.Path(f).touch(exist_ok=True)
    return rv


@app.get('/update_mat')
async def ep_update_mat():
    d = api_ddt_get_folder_path_root()
    return _ep_update('update_mat', f'{d}/pop_mat.sh')


@app.get('/kill_ddh')
async def ep_kill_ddh():
    d = dict()
    for i in ('main_ddh', 'main_ddh_controller',
              'main_dds', 'main_dds_controller'):
        rv = _sh(f'killall {i}')
        s = rv.stderr.decode().replace('\n', '')
        if rv.returncode == 0:
            s = CTT_API_OK
        if 'no process found' in s:
            s = 'N/A'
        # shorter name
        j = i.replace('main_', '')
        d[j] = s
    return d


@app.get('/kill_api')
async def ep_kill_api():
    _sh('killall main_api')
    # does not matter, won't answer
    return {'kill_api': CTT_API_OK}


@app.get('/force_reboot')
async def ep_force_reboot():
    if api_linux_is_rpi():
        _sh('sudo reboot')
        # does not matter, won't answer
        return {'force_reboot': CTT_API_OK}
    return {'force_reboot': 'not a raspberry'}


@app.get('/ddh_clear_lock_out_time')
async def ep_clear_lock_out_time():
    try:
        p = api_get_ddh_folder_path_macs_black()
        for f in glob.glob(f"{p}/*"):
            os.unlink(f)
            print(f'removing black mac {f}')
    except (OSError, Exception) as ex:
        print(f'error ep_clear_lock_out_time -> {ex}')

    pathlib.Path(TMP_PATH_DDH_APP_OVERRIDE).touch()
    print("API: BLE op conditions override set as 1")
    return {'ddh_clear_lock_out_time': CTT_API_OK}


@app.get("/cron_ena")
async def ep_crontab_enable():
    if not api_linux_is_rpi():
        return {'cron_ena': 'not RPi, not enabling crontab'}
    api_set_crontab(1)
    return {'cron_ena': api_get_crontab_ddh()}


@app.get("/cron_dis")
async def ep_crontab_disable():
    if not api_linux_is_rpi():
        return {'cron_dis': 'not RPi, not disabling crontab'}
    api_set_crontab(0)
    return {'cron_dis': api_get_crontab_ddh()}


@app.get("/api_version")
async def ep_api_version():
    return {'api_version': api_get_api_version()}


@app.get("/rpi_temperature")
async def ep_rpi_temperature():
    if not api_linux_is_rpi():
        return {'cron_dis': 'not RPi, not measuring board temperature'}
    c = "/usr/bin/vcgencmd measure_temp"
    rv = sp.run(c, shell=True, stderr=sp.PIPE, stdout=sp.PIPE)

    try:
        ans = rv.stdout
        if ans:
            # ans: b"temp=30.1'C"
            ans = ans.replace(b"\n", b"")
            ans = ans.replace(b"'C", b"")
            ans = ans.replace(b"temp=", b"")
            ans = float(ans.decode())
            return {'rpi_temperature': str(ans)}
    except (Exception,):
        return {'rpi_temperature': CTT_API_ER}


@app.get("/provision")
async def ep_provision():
    sn = dds_get_cfg_box_sn()
    prj = dds_get_cfg_box_project()
    addr = DDN_API_PROVISIONING_IP
    port = DDN_API_PROVISIONING_PORT
    ip_ddh = api_get_ip_vpn()
    dl_zip_file = get_files_from_server(prj, sn, ip_ddh, addr, port=port)
    if not dl_zip_file:
        print('error: DDH API running ep_provision')
        raise HTTPException(status_code=503, detail="provision error")
    _sh(f'unzip -o {dl_zip_file} -d /tmp')
    if not api_linux_is_rpi():
        return

    # separator
    _p('')

    fc = f'/tmp/config.toml'
    d = '/home/pi/li/ddh/settings'
    _p(f'moving {fc} to DDH settings folder')
    # todo ---> reenable this moving of config.toml file
    # _sh(f'mv {fc} {d}')

    fa = f'/tmp/all_macs.toml'
    s = f'moving {fa} to DDH settings folder'
    _p(s)
    rv = _sh(f'mv {fa} {d}')
    if rv.returncode:
        print('error provision: ' + s)
        return {'provision': CTT_API_ER}

    # fw = f'/tmp/wg0.conf'
    # _p(f'moving {fw} to wireguard settings folder')
    # _sh(f"sudo mv {fw} /etc/wireguard/")
    # _p('restarting DDH wireguard service')
    # _sh("sudo systemctl restart wg-quick@wg0.service")
    # _p('enabling DDH wireguard service')
    # _sh("sudo systemctl enable wg-quick@wg0.service")

    fd = f'/tmp/sshd_config'
    rv = _sh(f'sudo chmod 644 {fd}')
    if rv.returncode:
        print('error provision: chmod sshd_config')
        return {'provision': CTT_API_ER}
    _p(f'moving {fd} to /etc/ssh')
    rv = _sh(f'sudo mv {fd} /etc/ssh')
    if rv.returncode:
        print('error provision: move sshd_config')
        return {'provision': CTT_API_ER}

    fs = f'/tmp/authorized_keys'
    _p(f'moving {fs} to /home/pi/.ssh')
    _sh(f'mkdir -p /home/pi/.ssh')
    rv = _sh(f'sudo mv {fs} /home/pi/.ssh/')
    if rv.returncode:
        print('error provision: move authorized_keys')
        return {'provision': CTT_API_ER}
    rv = _sh('sudo chmod 600 /home/pi/.ssh/authorized_keys')
    if rv.returncode:
        print('error provision: chmod authorized_keys')
        return {'provision': CTT_API_ER}
    rv = _sh("sudo systemctl restart ssh")
    if rv.returncode:
        print('error provision: restart ssh')
        return {'provision': CTT_API_ER}
    return {'provision': CTT_API_OK}


@app.get("/test_crash")
async def ep_api_test_crash():
    # just lose it
    os._exit(-1)


@app.get("/ddh_side_button_2")
async def ep_api_ddh_side_button_2():
    api_ddh_side_button_2()
    return {'ddh_side_button_2': CTT_API_OK}


def _alarm_api_crash(n):
    if n == 0:
        return
    print(f'error: _alarm_api_crash, n = {n}')
    global g_ts_last_email_api_crash
    now = time.perf_counter()
    if g_ts_last_email_api_crash == 0 or \
       now > g_ts_last_email_api_crash + 300:
        g_ts_last_email_api_crash = now
        api_send_email_crash()


def main_api():
    # docs at http://0.0.0.0:port/docs
    setproctitle.setproctitle(NAME_EXE_API)
    uvicorn.run(app, host="0.0.0.0", port=DDH_PORT_API)


def controller_main_api():
    s = f"{NAME_EXE_API}_controller"
    setproctitle.setproctitle(s)
    print(f"=== {s} started ===")

    # kill any old son
    ne = NAME_EXE_API
    c = (f'(ps -aux | grep -w {ne} | grep -v grep) '
         f'&& echo "kill loose API" && killall {ne} && sleep 3')
    sp.run(c, shell=True)

    while 1:
        print(f"=== {s} launching child ===")
        p = Process(target=main_api)
        p.start()
        p.join()
        _alarm_api_crash(p.exitcode)
        print(f"=== {s} waits child, exitcode {p.exitcode} ===")
        time.sleep(5)


if __name__ == "__main__":

    if not api_linux_is_rpi():
        # debug: run without DDS controller
        main_api()
        sys.exit(0)

    if not api_linux_is_process_running(NAME_EXE_API_CONTROLLER):
        controller_main_api()
    else:
        print(f"not launching {NAME_EXE_API_CONTROLLER}, already running at python level")
