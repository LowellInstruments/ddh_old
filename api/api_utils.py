import glob
import json
import subprocess as sp


def shell(c):
    return sp.run(c, shell=True, stdout=sp.PIPE, stderr=sp.PIPE)


def _get_remote_commit(s):
    assert s in ('mat', 'ddh', 'ddt', 'liu')
    url = 'https://github.com/lowellinstruments/{}.git'.format(s)
    c = 'git ls-remote {} refs/heads/master'.format(url)
    rv = shell(c)
    if rv.returncode == 0:
        a = rv.stdout.decode().split()
        # a: dd3d0a...	refs/heads/master
        return a[0]


def _get_local_commit(s):
    # main_api.py runs in ddh root
    assert s in ('ddh', 'ddt')
    c = 'cd ../{} && git log -1 | grep commit | cut -f 2 -d " "'.format(s)
    rv = shell(c)
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
    c = 'cat /etc/com_{}_loc.txt'.format(s)
    rv = shell(c)
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


def get_boat_sn():
    c = 'cat run_dds.sh | grep DDH_BOX_SERIAL_NUMBER'
    rv = shell(c)
    sn = ''
    if rv.returncode == 0:
        sn = rv.stdout.decode().replace('\n', '').split('=')[1]
    return sn


def get_boat_project():
    c = 'cat run_dds.sh | grep DDH_BOX_PROJECT_NAME'
    rv = shell(c)
    prj = ''
    if rv.returncode == 0:
        prj = rv.stdout.decode().replace('\n', '').split('=')[1]
    return prj


def _get_iface_ip(iface):
    # src: stackoverflow 8529181
    if iface not in ('wg0', 'wlan0', 'ppp0'):
        return ''
    c = "ip -4 addr show {} | grep inet ".format(iface)
    rv = shell(c)
    ip = ''
    if rv.returncode == 0:
        # ['inet', '10.0.0.205/24', 'brd', ...]
        ip = rv.stdout.decode().split()[1].split('/')[0]
    return ip


def get_ip_vpn():
    return _get_iface_ip('wg0')


def get_ip_wlan():
    return _get_iface_ip('wlan0')


def get_ip_cell():
    return _get_iface_ip('ppp0')


def get_crontab_ddh():
    c = 'cat /etc/crontab | grep crontab_ddh.sh'
    rv = shell(c)
    if rv.returncode:
        # no "crontab_ddh.sh" string found in whole crontab
        return -1

    c = 'cat /etc/crontab | grep crontab_ddh.sh | grep "#"'
    rv = shell(c)
    if rv.returncode == 0:
        # string "# crontab_ddh.sh" found, but it is disabled
        return 0
    return 1


def set_crontab(on_flag):
    assert on_flag in (0, 1)
    s = get_crontab_ddh()
    c = ''
    print('s {} on_flag {}'.format(s, on_flag))
    if s == -1 and on_flag:
        # crontab empty, create it
        # todo: test this
        c = 'echo "* * * * * pi /home/pi/li/ddt/_dt_files/crontab_ddh.sh" > /etc/crontab'
    if s == 0 and on_flag:
        # is disabled, uncomment it
        print('uncommenting')
        c = "sudo sed -i '/crontab_ddh.sh/s/^#//g' /etc/crontab"
    if s == 1 and not on_flag:
        # is enabled, comment it
        print('commenting')
        c = "sudo sed -i '/crontab_ddh.sh/s/^/#/g' /etc/crontab"
    rv = shell(c)
    if rv.returncode == 0:
        # need to restart crontab service
        c = "sudo systemctl restart crond.service"
        rv = shell(c)
        return rv.returncode == 0


def get_running():
    rv_h = shell('ps -aux | grep "main_ddh" | grep -v grep')
    rv_s = shell('ps -aux | grep "main_dds" | grep -v grep')
    rv_hc = shell('ps -aux | grep "main_ddh_controller" | grep -v grep')
    rv_hs = shell('ps -aux | grep "main_dds_controller" | grep -v grep')
    return {
        'is_ddh_running': rv_h.returncode == 0,
        'is_dds_running': rv_s.returncode == 0,
        'is_ddh_controller_running': rv_hc.returncode == 0,
        'is_dds_controller_running': rv_hs.returncode == 0
    }


def get_ble_state():
    h = '/usr/bin/hciconfig'
    rv_0 = shell('{} -a | grep hci0'.format(h))
    rv_1 = shell('{} -a | grep hci1'.format(h))
    d = dict()
    d['hci0_present'] = False
    d['hci1_present'] = False
    d['hci0_running'] = False
    d['hci1_running'] = False
    if rv_0.returncode == 0:
        d['hci0_present'] = True
        rv = shell('{} hci0'.format(h))
        d['hci0_running'] = 'UP RUNNING' in rv.stdout.decode()
    if rv_1.returncode == 0:
        d['hci1_present'] = True
        rv = shell('{} hci1'.format(h))
        d['hci1_running'] = 'UP RUNNING' in rv.stdout.decode()
    return d


def get_gps():
    g = ''
    try:
        with open('/tmp/gps_last.json', 'r') as f:
            g = json.load(f)
    except (Exception, ):
        pass
    return g


def get_versions():
    v_mat_l = get_git_commit_mat_local()
    v_mat_r = get_git_commit_mat_remote()
    v_ddh_l = get_git_commit_ddh_local()
    v_ddh_r = get_git_commit_ddh_remote()
    v_ddt_l = get_git_commit_ddt_local()
    v_ddt_r = get_git_commit_ddt_remote()
    v_liu_l = get_git_commit_liu_local()
    v_liu_r = get_git_commit_liu_remote()
    return {
        'need_mat_update': 'yes' if v_mat_l != v_mat_r else 'no',
        'need_ddh_update': 'yes' if v_ddh_l != v_ddh_r else 'no',
        'need_ddt_update': 'yes' if v_ddt_l != v_ddt_r else 'no',
        'need_liu_update': 'yes' if v_liu_l != v_liu_r else 'no'
    }


def get_logger_mac_reset_files():
    ff = glob.glob('api/*.rst')
    return {'mac_reset_files': ff}
