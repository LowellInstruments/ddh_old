import subprocess as sp


LIST_CONF_FILES = {
    'settings/ddh.json',
    'run_dds.sh',
    'settings/_li_all_macs_to_sn.yml',
    '/etc/crontab'
}


def shell(c):
    return sp.run(c, shell=True, stdout=sp.PIPE, stderr=sp.PIPE)


def _get_remote_commit(s):
    assert s in ('mat', 'ddh', 'ddt')
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


def get_git_commit_mat_local():
    # MAT is installed so different way to get the commit
    c = 'cat /etc/com_mat_loc.txt'
    rv = shell(c)
    commit_id = ''
    if rv.returncode == 0:
        commit_id = rv.stdout.decode().replace('\n', '')
    return commit_id


def get_git_commit_ddt_local():
    return _get_local_commit('ddt')


def get_git_commit_ddt_remote():
    return _get_remote_commit('ddt')


def get_boat_sn():
    c = 'cat run_dds.sh | grep DDH_BOX_SERIAL_NUMBER'
    rv = shell(c)
    sn = ''
    if rv.returncode == 0:
        sn = rv.stdout.decode().replace('\n', '').split('=')[1]
    return sn


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


def get_crontab():
    c = 'cat /etc/crontab | grep crontab_ddh.sh'
    rv = shell(c)
    if rv.returncode:
        # no "crontab_ddh.sh" string found in whole crontab
        return False

    c = 'cat /etc/crontab | grep crontab_ddh.sh | grep "#"'
    rv = shell(c)
    if rv.returncode == 0:
        # string "# crontab_ddh.sh" found, but it is disabled
        return False
    return True


def set_crontab(on_flag):
    # todo: test this
    assert on_flag in (0, 1)
    s = get_crontab()
    c = ''
    if s == 0 and on_flag:
        # is disabled, uncomment it
        c = "sudo sed -i '/crontab_ddh.sh/s/^#//g' /etc/crontab"
    if s == 1 and not on_flag:
        # is enabled, comment it
        c = "sudo sed -i '/crontab_ddh.sh/s/^/#/g' /etc/crontab"
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
