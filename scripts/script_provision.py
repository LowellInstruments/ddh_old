#!/usr/bin/env python3


import os
import pathlib
import shutil
import subprocess as sp
import time

import toml


DDN_API_PORT = 9000
DDN_ADDR = 'ddn.lowellinstruments.com'
HOME = str(pathlib.Path.home())
FOL_VPN = f'{HOME}/.ddh_vpn'
PBF = f'{HOME}/.ddh_prov_req.toml'
FOL_ANSWER = '/tmp/.ddh_prov_ans'


def _p(s):
    print(f'[ PRV ] {s}')


def _sh(c):
    rv = sp.run(c, shell=True, stderr=sp.PIPE, stdout=sp.PIPE)
    return rv.returncode


def _is_rpi():
    return _sh('cat /proc/cpuinfo | grep aspberry') == 0


def _create_vpn_keys():
    os.makedirs(FOL_VPN, exist_ok=True)
    kip = f'{FOL_VPN}/.key_pri'
    kup = f'{FOL_VPN}/.key_pub'
    rvi = _sh(f'wg genkey > {kip}')
    rvu = _sh(f'wg pubkey < {kip} > {kup}')
    if rvi or rvu:
        print('error: _create_vpn_keys')
        return
    _sh(f'chmod 600 {kip}')
    rv = sp.run(f'cat {kip}', shell=True, stdout=sp.PIPE)
    ki = rv.stdout.replace(b'\n', b'').decode()
    rv = sp.run(f'cat {kup}', shell=True, stdout=sp.PIPE)
    ku = rv.stdout.replace(b'\n', b'').decode()
    return ki, ku


def curl_get_files_from_server(pr, sn, ip, addr='0.0.0.0', port=DDN_API_PORT):

    # ensuring the results will be new
    d = FOL_ANSWER
    if os.path.exists(d):
        shutil.rmtree(d)
    os.makedirs(d)

    # ------------------------------
    # file 1 of 3: obtain VPN info
    # ------------------------------
    kk = _create_vpn_keys()
    if not kk:
        return 1
    ki, ku = kk
    _p(f'generated private key {ki}')
    _p(f'generated public key {ku}')
    dst = f'{d}/wg0.conf'
    if os.path.exists(dst):
        os.unlink(dst)
    rvv = _sh("curl -X 'GET' "
              f"'http://{addr}:{port}/vpn/v1?prj={pr}&sn={sn}&ip={ip}&ku={ku}' "
              f"-H 'accept: application/json' -o {dst}")
    if rvv:
        raise Exception(f"error curl VPN, prj {pr} sn {sn} ip {ip}")
    rv = sp.run(f'cat {dst}', shell=True, stdout=sp.PIPE)
    wg = rv.stdout.decode()
    with open(dst, 'w') as f:
        f.write(wg.format(ki))
    _p(f'OK: got file {dst}')

    # -------------------------------------------------
    # file 2 of 3: obtain DDH settings file config.toml
    # -------------------------------------------------
    dst = f'{d}/config.toml'
    if os.path.exists(dst):
        os.unlink(dst)
    rvc = _sh("curl -f -X 'GET' "
              f"'http://{addr}:{port}/ddh_config/v1?prj={pr}&sn={sn}' "
              f"-H 'accept: application/json' -o {dst}")
    if rvc:
        raise Exception(f"error curl config.toml, prj {pr} sn {sn} ip {ip}")
    _p(f'OK: got file {dst}')

    # ----------------------------------------------------
    # file 3 of 3: obtain DDH settings file all_macs.toml
    # ----------------------------------------------------
    dst = f'{d}/all_macs.toml'
    if os.path.exists(dst):
        os.unlink(dst)
    rvm = _sh("curl -f -X 'GET' "
              f"'http://{addr}:{port}/all_macs/v1?prj={pr}' "
              f"-H 'accept: application/json' -o {dst}")
    if rvm:
        raise Exception(f"error curl all_macs, prj {pr} sn {sn} ip {ip}")
    _p(f'OK: got file {dst}')


def _read_provision_bootstrap_file():
    with open(PBF, 'r') as f:
        c = toml.load(f)
    pr = c['provision']['boat_prj']
    sn = c['provision']['boat_sn']
    ip = c['provision']['vpn_ip']
    _p(f'read provision request file: prj {pr} sn {sn} ip {ip}')
    return pr, sn, ip


def _provision_ddh(a=DDN_ADDR):
    pr, sn, ip = _read_provision_bootstrap_file()
    curl_get_files_from_server(pr, sn, ip, a)
    if _is_rpi():
        # we have VPN keys in FOL_VPN
        # we have the obtained files in FOL_RESULT
        d = '/home/pi/li/ddh/settings'
        p = f'{FOL_ANSWER}/config.toml'
        _p(f'moving {p} to DDH settings folder')
        _sh(f'mv {p} {d}')
        p = f'{FOL_ANSWER}/all_macs.toml'
        _p(f'moving {p} to DDH settings folder')
        _sh(f'mv {p} {d}')
        p = f'{FOL_ANSWER}/wg0.conf'
        _p(f'moving {p} to wireguard settings folder')
        d = '/etc/wireguard'
        _sh(f"sudo mv {p} {d}")
        _p('restarting DDH wireguard service')
        _sh("sudo systemctl restart wg-quick@wg0.service")

        # get rid of the file so only executes once
        os.unlink(PBF)


def provision_ddh(a=DDN_ADDR):
    """

    # example bootstrap provision file /home/pi/.ddh_prov_req.toml'
    [provision]
    vpn_ip="1.2.3.4"
    boat_sn="1234567"
    boat_prj="kaz"

    """
    try:
        _provision_ddh(a)
    except (Exception, ) as ex:
        # such as "no bootstrap provision file"
        _p(f'\nexception provision_ddh -> {str(ex)}')
    finally:
        # see any message
        time.sleep(5)


if __name__ == '__main__':
    provision_ddh()
    # provision('0.0.0.0')
