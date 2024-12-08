import copy
import pathlib
import time

import toml
import os
import subprocess as sp

from utils.flag_paths import (
    TMP_PATH_GRAPH_TEST_MODE_JSON,
    LI_PATH_DDH_GPS_EXTERNAL,
    LI_PATH_TEST_MODE,
)


def sh(c):
    rv = sp.run(c, shell=True, stdout=sp.PIPE, stderr=sp.PIPE)
    return rv.returncode


def ddh_get_folder_path_scripts() -> pathlib.Path:
    p = pathlib.Path.home()
    if is_rpi():
        return pathlib.Path(str(p) + '/li/ddh/scripts')
    return pathlib.Path(str(p) + '/PycharmProjects/ddh/scripts')


def is_rpi():
    return sh('cat /proc/cpuinfo | grep aspberry') == 0


def _get_config_file_path():
    p = pathlib.Path.home()
    if is_rpi():
        return str(p) + '/li/ddh/settings/config.toml'
    return str(p) + '/PycharmProjects/ddh/settings/config.toml'


def _check_monitored_macs_in_cfg_file(c):
    for k, v in c['monitored_macs'].items():
        if '-' in k:
            print('error: "-" symbol in monitored macs, use ":"')
            time.sleep(2)
            os._exit(1)
        if type(k) is not str:
            print(f'error: {k} in config file is not a string')
            time.sleep(2)
            os._exit(1)
        if type(v) is not str:
            print(f'error: {v} in config file is not a string')
            time.sleep(2)
            os._exit(1)


def cfg_load_from_file():
    try:
        p = _get_config_file_path()
        with open(p, 'r') as f:
            c = toml.load(f)
            _check_monitored_macs_in_cfg_file(c)
            return c
    except (Exception, ) as ex:
        print('error: cfg_load_from_file: ', ex)
        os._exit(1)


def cfg_save_to_file(c):
    try:
        p = _get_config_file_path()
        with open(p, 'w') as f:
            toml.dump(c, f)
    except (Exception, ) as ex:
        print('error: cfg_save_to_file: ', ex)
        os._exit(1)


cfg = cfg_load_from_file()


def dds_get_cfg_vessel_name():
    return cfg['behavior']['ship_name']


def dds_get_cfg_aws_en():
    return cfg['flags']['aws_en']


def dds_get_cfg_gpq_en():
    return cfg['flags']['gpq_en']


def dds_get_cfg_skip_dl_in_port_en():
    rv = cfg['flags']['skip_dl_in_port_en']
    return rv


def dds_get_cfg_flag_graph_test_mode():
    return os.path.exists(TMP_PATH_GRAPH_TEST_MODE_JSON)


def dds_get_cfg_flag_download_test_mode():
    return os.path.exists(LI_PATH_TEST_MODE)


def dds_get_cfg_flag_gps_external():
    return os.path.exists(LI_PATH_DDH_GPS_EXTERNAL)


def dds_get_cfg_flag_gps_error_forced():
    return cfg['flags']['hook_gps_error_measurement_forced']


def dds_get_cfg_monitored_serial_numbers():
    return list(cfg['monitored_macs'].values())


def dds_get_cfg_monitored_macs():
    ls = list(cfg['monitored_macs'].keys())
    return [i.lower() for i in ls]


def dds_get_cfg_monitored_pairs():
    return cfg['monitored_macs']


def dds_get_cfg_fake_gps_position():
    return cfg['behavior']['fake_gps_position']


def dds_get_cfg_forget_time_secs():
    return int(cfg['behavior']['forget_time'])


def dds_get_cfg_logger_sn_from_mac(mac):
    mac = mac.lower()

    # happens when g_graph_test_mode()
    test_graph_d = {
        '00:00:00:00:00:00': 'test000',
        '11:22:33:44:55:66': 'test111',
        '99:99:99:99:99:99': 'test999',
        '55:55:55:55:55:55': 'test555',
        '33:33:33:33:33:33': 'test333'
    }
    if mac in test_graph_d.keys():
        return test_graph_d[mac]

    # do it like this to avoid case errors
    for k, v in cfg['monitored_macs'].items():
        if mac == k.lower():
            return v.lower()


def dds_get_cfg_logger_mac_from_sn(sn):

    sn = sn.lower()

    # happens when g_graph_test_mode()
    test_graph_d = {
        'test000': '00:00:00:00:00:00',
        'test111': '11:22:33:44:55:66',
        'test999': '99:99:99:99:99:99',
        'test555': '55:55:55:55:55:55',
        'test333': '33:33:33:33:33:33',
    }
    if sn in test_graph_d.keys():
        return test_graph_d[sn]

    # do it like this to avoid case errors
    for k, v in cfg['monitored_macs'].items():
        if sn == v.lower():
            return k.lower()


def ddh_get_cfg_gear_type():
    # 0 normal 1 trawling
    return cfg['behavior']['gear_type']


def dds_check_config_file():
    b = copy.deepcopy(cfg)
    aux = None
    try:
        for i in [
            'aws_en',
            'sqs_en',
            'ble_en',
            'gpq_en',
            'maps_en',
            'sms_en',
            'skip_dl_in_port_en',
            'hook_gps_error_measurement_forced',
            'hook_ble_purge_black_macs_on_boot',
            'hook_ble_purge_this_mac_dl_files_folder'
        ]:
            aux = i
            del b['flags'][i]
    except (Exception, ) as ex:
        print(f'error: dds_check_cfg_has_all_flags -> {ex}')
        print(f'error: missing flag {aux}')
        return aux

    aux = b['flags']
    if len(aux):
        print(f'error: dds_check_cfg_has_all_flags')
        print(f'error: unexpected flags {aux}')
        return aux

    # monitored macs checked in _check_monitored_macs_in_cfg_file()

    assert type(b['behavior']['moving_speed']) is list
    assert type(b['behavior']['fake_gps_position']) is list


def dds_check_cfg_has_box_info():
    sn = cfg['credentials']['cred_ddh_serial_number']
    if not sn:
        print('***********************')
        print('  error! need box sn')
        print('***********************')
        os._exit(1)
    prj = cfg['credentials']['cred_ddh_project_name']
    if not prj:
        print('********************************')
        print('  error: need box project name')
        print('********************************')
        os._exit(1)


def dds_get_cfg_flag_purge_black_macs_on_boot():
    return cfg['flags']['hook_ble_purge_black_macs_on_boot']


def dds_get_cfg_flag_purge_this_mac_dl_files_folder():
    return cfg['flags']['hook_ble_purge_this_mac_dl_files_folder']


def dds_get_cfg_moving_speed():
    return cfg['behavior']['moving_speed']


def dds_get_cfg_flag_ble_en():
    # works altogether with file TMP_PATH_DISABLE_BLE
    return cfg['flags']['ble_en']


def dds_get_cfg_flag_sqs_en():
    return cfg['flags']['sqs_en']


def dds_get_cfg_aws_credential(k):
    assert k in cfg['credentials'].keys() \
           and k.startswith("cred_aws_")
    return cfg['credentials'][k]


def dds_get_cfg_box_sn():
    return cfg["credentials"]["cred_ddh_serial_number"]


def dds_get_cfg_box_project():
    return cfg["credentials"]["cred_ddh_project_name"]


def ddh_get_cfg_maps_en():
    try:
        return int(cfg['flags']['maps_en'])
    except (Exception, ):
        return False


def _get_exp_key_from_cfg(k):
    try:
        return cfg['experimental'][k]
    except (Exception, ) as ex:
        # print(f'error: _get_exp_key_from_cfg -> {ex}')
        # no value in [experimental] section
        return -1


def exp_get_use_lsb_for_tdo_loggers():
    return _get_exp_key_from_cfg('use_lsb_for_tdo_loggers')


def exp_get_use_lsb_for_dox_loggers():
    return _get_exp_key_from_cfg('use_lsb_for_dox_loggers')


def exp_get_use_aws_cp():
    return _get_exp_key_from_cfg('use_aws_cp')


def exp_get_use_ble_passive_scanning():
    return _get_exp_key_from_cfg('use_ble_passive_scanning')


def exp_get_ble_do_crc():
    return _get_exp_key_from_cfg('ble_do_crc')


def exp_get_conf_tdo():
    rv = _get_exp_key_from_cfg('conf_tdo')
    if rv == -1:
        # no such key in config.toml
        return
    if rv == 'none':
        # empty dictionary, DDH client will just send nothing
        return {}
    if rv not in ('slow', 'mid', 'fast'):
        print('rv NOT in expt_get_conf_tdo() possible keys')
        return
    fol = ddh_get_folder_path_scripts()
    filename = f'script_logger_tdo_deploy_cfg_{rv}.toml'
    path_prf_file = f'{fol}/{filename}'
    if not os.path.exists(path_prf_file):
        return
    try:
        with open(path_prf_file, 'r') as f:
            d = toml.load(f)['profiling']
            d['mode'] = rv
            return d
    except (Exception, ) as ex:
        print(f'error exp_get_conf_tdo() -> {ex}')


def exp_get_conf_dox():
    rv = _get_exp_key_from_cfg('conf_dox')
    if rv == -1:
        # no such key in config.toml
        return
    if rv not in (60, 300, 900, "60", "300", "900"):
        print('rv NOT in expt_get_conf_dox() possible keys')
        return
    return int(rv)


def exp_get_use_smart_lock_out_time():
    return _get_exp_key_from_cfg('use_smart_lock_out_time')


if __name__ == '__main__':
    print('vessel_name', dds_get_cfg_vessel_name())
    print('aws_en', dds_get_cfg_aws_en())
    print('flag_graph_test', dds_get_cfg_flag_graph_test_mode())
    print('flag_gps_external', dds_get_cfg_flag_gps_external())
    print('flag_gps_error_forced', dds_get_cfg_flag_gps_error_forced())
    print('ls_sn_macs', dds_get_cfg_monitored_serial_numbers())
    print('json_mac_dns', dds_get_cfg_logger_sn_from_mac("11-22-33-44-55-66"))
    print('ft', dds_get_cfg_forget_time_secs())
    print('monitored_macs', dds_get_cfg_monitored_macs())
    print('mac_from_sn_json_file', dds_get_cfg_logger_mac_from_sn('1234567'))
    print('gear_type', ddh_get_cfg_gear_type())
    print('check_we_have_box_env_info', dds_check_cfg_has_box_info())
    print('purge_black_macs_on_boot', dds_get_cfg_flag_purge_black_macs_on_boot())
    print('purge_mac_dl_files_folder', dds_get_cfg_flag_purge_this_mac_dl_files_folder())
    print('get_moving_speed', dds_get_cfg_moving_speed())
    print('dds_get_flag_sqs_en', dds_get_cfg_flag_sqs_en())
    print('ddh_flag_maps_en', ddh_get_cfg_maps_en())
    print('conf_tdo', exp_get_conf_tdo())
    print('conf_dox', exp_get_conf_dox())
