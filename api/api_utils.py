import datetime
import glob
import json
import os
import pathlib
import platform
import subprocess as sp
import sys
import time


CTT_API_OK = 'ok'
CTT_API_ER = 'error'


def _sh(c):
    rv = sp.run(c, shell=True, stdout=sp.PIPE, stderr=sp.PIPE)
    if rv.returncode:
        e = ''
        e += '----------------\n'
        e += f'{datetime.datetime.now()}\n'
        e += f'command {c} returned {rv.returncode}\n'
        e += f'    stdout     {rv.stdout.decode()}\n'
        e += f'    stderr     {rv.stderr.decode()}\n'
        e += '----------------\n'
        print(e)
        with open('/tmp/debug_api.txt', 'a') as f:
            f.write(e)
        # o/wise output not shown in journalctl
        #   $ journalctl -u unit_switch_net.service
        sys.stdout.flush()
    return rv


def linux_is_rpi():
    if platform.system() == 'Windows':
        return False
    # better than checking architecture
    return os.uname().nodename in ('raspberrypi', 'rpi')


_r = str(pathlib.Path.home())
_r += '/li' if linux_is_rpi() else '/PycharmProjects'


def api_get_full_ddh_config_file_path():
    return _r + '/ddh/settings/config.toml'


def api_get_folder_path_root():
    return _r + '/ddh'


def ddt_get_folder_path_root():
    return _r + '/ddt'


def _get_remote_commit(s):
    assert s in ('mat', 'ddh', 'ddt', 'liu')
    url = f'https://github.com/lowellinstruments/{s}.git'
    c = f'git ls-remote {url} refs/heads/master'
    rv = _sh(c)
    if rv.returncode == 0:
        a = rv.stdout.decode().split()
        # a: dd3d0a...	refs/heads/master
        return a[0]


def _get_local_commit(s):
    # main_api.py runs in ddh root
    assert s in ('ddh', 'ddt')
    c = f'cd ../{s} && git log -1 | grep commit | cut -f 2 -d " "'
    rv = _sh(c)
    s = rv.stdout.decode().replace('\n', '')
    return s


def get_git_commit_ddh_remote():
    return _get_remote_commit('ddh')


def get_git_commit_ddh_local():
    return _get_local_commit('ddh')


def get_git_commit_mat_remote():
    return _get_remote_commit('mat')


def _get_git_commit_mat_local_from_file(s):
    # MAT is installed so different way to get the commit
    c = f'cat /etc/com_{s}_loc.txt'
    rv = _sh(c)
    commit_id = ''
    if rv.returncode == 0:
        commit_id = rv.stdout.decode().replace('\n', '')
    return commit_id


def get_git_commit_mat_local():
    return _get_git_commit_mat_local_from_file('mat')


def get_git_commit_liu_local():
    return _get_git_commit_mat_local_from_file('liu')


def get_git_commit_ddt_local():
    return _get_local_commit('ddt')


def get_git_commit_ddt_remote():
    return _get_remote_commit('ddt')


def get_git_commit_liu_remote():
    return _get_remote_commit('liu')


def _get_iface_ip(iface):
    # src: stackoverflow 8529181
    if iface not in ('wg0', 'wlan0', 'ppp0'):
        return ''
    c = "ip -4 addr show {} | grep inet ".format(iface)
    rv = _sh(c)
    ip = ''
    if rv.returncode == 0:
        # ['inet', '10.0.0.205/24', 'brd', ...]
        ip = rv.stdout.decode().split()[1].split('/')[0]
    return ip


def get_ip_vpn():
    return _get_iface_ip('wg0')


def get_timezone():
    # dirty but works
    c = 'timedatectl | grep "Time zone"'
    rv = _sh(c)
    if rv.returncode == 0:
        # b'Time zone: America/New_York (EDT, -0400)'
        return rv.stdout.decode().split(': ')[1]
    return f'{CTT_API_ER}: get_local_timezone()'


def get_utc_epoch():
    return int(time.time())


def get_ip_wlan():
    return _get_iface_ip('wlan0')


def get_ip_cell():
    return _get_iface_ip('ppp0')


def get_uptime():
    c = 'uptime -p'
    rv = _sh(c)
    s = rv.stdout.decode()
    # s: "up 3 days, 14 hours, 29 minutes\n"
    s = s[3:-1]
    s = s.replace(' years', 'y')
    s = s.replace(' months', 'm')
    s = s.replace(' days', 'd')
    s = s.replace(' hours', 'h')
    s = s.replace(' minutes', 'mi')
    s = s.replace(',', '')
    return s


def get_uptime_secs():
    c = "awk '{print $1}' /proc/uptime"
    rv = _sh(c)
    s = rv.stdout.decode().replace('\n', '')
    return int(float(s))


def _get_crontab(s):
    c = f'cat /etc/crontab | grep crontab_{s}.sh'
    rv = _sh(c)
    if rv.returncode:
        # no "crontab_*.sh" string found in whole crontab
        return -1

    c = f'cat /etc/crontab | grep crontab_{s}.sh | grep "#"'
    rv = _sh(c)
    if rv.returncode == 0:
        # string "# crontab_*.sh" found, but it is disabled
        return 0
    return 1


def get_crontab_ddh():
    return _get_crontab('ddh')


def get_crontab_api():
    return _get_crontab('api')


def set_crontab(on_flag):
    # only for DDH, never for API
    assert on_flag in (0, 1)
    s = get_crontab_ddh()
    c = ''
    print('s {} on_flag {}'.format(s, on_flag))
    if s == -1 and on_flag:
        # crontab empty, create it
        c = 'echo "* * * * * pi /home/pi/li/ddt/_dt_files/crontab_ddh.sh" | sudo tee -a /etc/crontab'
    if s == 0 and on_flag:
        # is disabled, uncomment it
        print('uncommenting')
        c = "sudo sed -i '/crontab_ddh.sh/s/^#//g' /etc/crontab"
    if s == 1 and not on_flag:
        # is enabled, comment it
        print('commenting')
        c = "sudo sed -i '/crontab_ddh.sh/s/^/#/g' /etc/crontab"
    rv = _sh(c)
    if rv.returncode == 0:
        # need to restart crontab service
        c = "sudo systemctl restart crond.service"
        rv = _sh(c)
        return rv.returncode == 0


def get_running():
    rv_h = _sh('ps -aux | grep "main_ddh" | grep -v grep')
    rv_s = _sh('ps -aux | grep "main_dds" | grep -v grep')
    rv_hc = _sh('ps -aux | grep "main_ddh_controller" | grep -v grep')
    rv_hs = _sh('ps -aux | grep "main_dds_controller" | grep -v grep')
    return {
        'ddh': int(rv_h.returncode == 0),
        'dds': int(rv_s.returncode == 0),
        'ddh_controller': int(rv_hc.returncode == 0),
        'dds_controller': int(rv_hs.returncode == 0)
    }


def get_ble_state():
    h = '/usr/bin/hciconfig'
    rv_0 = _sh('{} -a | grep hci0'.format(h))
    rv_1 = _sh('{} -a | grep hci1'.format(h))
    d = dict()
    d['hci0_present'] = False
    d['hci1_present'] = False
    d['hci0_running'] = False
    d['hci1_running'] = False
    if rv_0.returncode == 0:
        d['hci0_present'] = True
        rv = _sh('{} hci0'.format(h))
        d['hci0_running'] = 'UP RUNNING' in rv.stdout.decode()
    if rv_1.returncode == 0:
        d['hci1_present'] = True
        rv = _sh('{} hci1'.format(h))
        d['hci1_running'] = 'UP RUNNING' in rv.stdout.decode()
    return d


def get_gps():
    try:
        with open('/tmp/gps_last.json', 'r') as f:
            return json.load(f)
    except (Exception, ) as ex:
        print(f'{CTT_API_ER}: cannot api_get_gps -> {ex}')
        return {}


def get_versions():
    v_mat_l = get_git_commit_mat_local()
    v_mat_r = get_git_commit_mat_remote()
    v_ddh_l = get_git_commit_ddh_local()
    v_ddh_r = get_git_commit_ddh_remote()
    v_ddt_l = get_git_commit_ddt_local()
    v_ddt_r = get_git_commit_ddt_remote()
    return {
        'need_mat_update': 'yes' if v_mat_l != v_mat_r else 'no',
        'need_ddh_update': 'yes' if v_ddh_l != v_ddh_r else 'no',
        'need_ddt_update': 'yes' if v_ddt_l != v_ddt_r else 'no',
    }


def get_logger_mac_reset_files():
    p = api_get_folder_path_root()
    ff = glob.glob(f'{p}/dds/tweak/*.rst')
    return ff


# let's repeat 2 functions here so API does not require MAT
def linux_app_write_pid_to_tmp(name):
    if not name.endswith('.pid'):
        name += '.pid'
    if not name.startswith('/tmp/'):
        name = '/tmp/' + name
    path = name
    pid = str(os.getpid())
    f = open(path, 'w')
    f.write(pid)
    f.close()


def api_read_aws_sqs_ts():
    # path relative to main_api.py
    p = "ddh/db/db_status.json"
    now = str(datetime.datetime.now(tz=datetime.timezone.utc))
    try:
        with open(p, 'r') as f:
            j = json.load(f)
    except (Exception, ):
        j = {
            'aws': ('unknown', now),
            'sqs': ('unknown', now)
        }
    return j


if __name__ == '__main__':
    # print(get_timezone())
    print(get_uptime_secs())
