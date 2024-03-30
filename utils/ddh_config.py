import toml
import os

from utils.tmp_paths import TMP_PATH_GRAPH_TEST_MODE_JSON, LI_PATH_DDH_GPS_EXTERNAL


def _get_relative_config_file_path():
    # when DDH
    if os.getcwd().endswith('ddh'):
        return 'settings/config.toml'
    # when developing / testing / running this file's main()
    return '../settings/config.toml'


def _check_cfg(c):
    for k, v in c['monitored_macs'].items():
        if '-' in k:
            print('error: "-" symbol in monitored macs, use ":"')
            os._exit(1)
        if type(k) is not str:
            print(f'error: {k} in config file is not a string')
            os._exit(1)
        if type(v) is not str:
            print(f'error: {v} in config file is not a string')
            os._exit(1)


def cfg_load_from_file():
    try:
        p = _get_relative_config_file_path()
        with open(p, 'r') as f:
            c = toml.load(f)
            _check_cfg(c)
            return c
    except (Exception, ) as ex:
        print('error: toml_cfg_read_file: ', ex)
        os._exit(1)


def cfg_save_to_file(c):
    try:
        p = _get_relative_config_file_path()
        with open(p, 'w') as f:
            toml.dump(c, f)
    except (Exception, ) as ex:
        print('error: toml_cfg_read_file: ', ex)
        os._exit(1)


cfg = cfg_load_from_file()


def dds_get_cfg_vessel_name():
    return cfg['behavior']['ship_name']


def dds_get_cfg_aws_en():
    return cfg['flags']['aws_en']


def dds_get_cfg_flag_graph_test_mode():
    return os.path.exists(TMP_PATH_GRAPH_TEST_MODE_JSON)


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


def dds_get_cfg_flag_rbl_en():
    return cfg['flags']['rbl_en']


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
    print('dds_get_flag_rbl_en', dds_get_cfg_flag_rbl_en())
    print('dds_get_flag_sqs_en', dds_get_cfg_flag_sqs_en())
    print('ddh_flag_maps_en', ddh_get_cfg_maps_en())
