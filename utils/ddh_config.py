import toml
import os

from utils.ddh_shared import get_ddh_rerun_flag

# when DDH
if os.getcwd().endswith('ddh'):
    PATH_FILE_CFG = 'settings/config.toml'
# when testing this file
else:
    PATH_FILE_CFG = '../settings/config.toml'


def _check_cfg(c):
    for k in c['monitored_macs'].keys():
        if '-' in k:
            print('error: "-" symbol in monitored macs, use ":"')
            os._exit(1)
    for k in c['all_macs'].keys():
        if '-' in k:
            print('error: "-" symbol in monitored macs, use ":"')
            os._exit(1)


def cfg_load(p=PATH_FILE_CFG):
    try:
        with open(p, 'r') as f:
            c = toml.load(f)
            _check_cfg(c)
            return c
    except (Exception, ) as ex:
        print('error: toml_cfg_read_file: ', ex)
        os._exit(1)


def cfg_save(c, p=PATH_FILE_CFG):
    try:
        with open(p, 'w') as f:
            return toml.dump(c, f)
    except (Exception, ) as ex:
        print('error: toml_cfg_read_file: ', ex)
        os._exit(1)


cfg = cfg_load()


def dds_get_json_vessel_name():
    return cfg['behavior']['ship_name']


def dds_get_aws_en():
    return cfg['flags']['aws_en']


def dds_get_flag_graph_test_mode():
    return cfg['flags']['hook_graph_test_mode']


def dds_get_flag_gps_external():
    return cfg['flags']['g_gps_is_external']


def dds_get_flag_gps_error_forced():
    return cfg['flags']['hook_gps_error_measurement_forced']


def dds_get_serial_number_of_macs_from_json_file():
    return list(cfg['monitored_macs'].values())


def dds_get_macs_from_json_file():
    return list(cfg['monitored_macs'].keys())


def dds_get_mac_n_sn_monitored_pairs_from_json_file():
    return cfg['monitored_macs']


def dds_get_all_macs():
    return cfg['all_macs']


def dds_get_json_mac_dns(mac):

    # happens when g_graph_test_mode()
    mac = mac.lower()
    test_graph_d = {
        '00:00:00:00:00:00': 'test000',
        '11:22:33:44:55:66': 'test111',
        '99:99:99:99:99:99': 'test999',
        '55:55:55:55:55:55': 'test555'
    }
    if mac in test_graph_d.keys():
        return test_graph_d[mac]

    return cfg['monitored_macs'][mac]


def dds_json_get_forget_time_secs():
    return int(cfg['behavior']['forget_time'])


def dds_get_mac_from_sn_from_json_file(sn):

    # happens when g_graph_test_mode()
    test_graph_d = {
        'test000': '00:00:00:00:00:00',
        'test111': '11:22:33:44:55:66',
        'test999': '99:99:99:99:99:99',
        'test555': '55:55:55:55:55:55'
    }
    if sn in test_graph_d.keys():
        return test_graph_d[sn]

    for k, v in cfg['monitored_macs'].items():
        if v.lower() == sn.lower():
            return k.lower()
    return None


def ddh_get_json_gear_type():
    return cfg['behavior']['gear_type']


def dds_check_we_have_box_env_info():
    sn = cfg['credentials']['cred_ddh_serial_number']
    if not sn:
        print('error: need box sn')
        os._exit(1)
    prj = cfg['credentials']['cred_ddh_project_name']
    if not prj:
        print('error: need box project name')
        os._exit(1)


def dds_get_flag_ble_purge_black_macs_on_boot():
    return cfg['flags']['hook_ble_purge_black_macs_on_boot']


def dds_get_flag_ble_purge_this_mac_dl_files_folder():
    return cfg['flags']['hook_ble_purge_this_mac_dl_files_folder']


def dds_get_moving_speed():
    return cfg['behavior']['moving_speed']


def dds_get_flag_ble_en():
    return cfg['flags']['ble_en']


def dds_get_flag_rbl_en():
    return cfg['flags']['rbl_en']


def dds_get_flag_sqs_en():
    return cfg['flags']['sqs_en']


def dds_get_aws_credential(k):
    assert k in cfg['credentials'].keys() \
           and k.startswith("cred_aws_")
    return cfg['credentials'][k]


def dds_get_box_sn():
    return cfg["credentials"]["cred_ddh_serial_number"]


def dds_get_box_project():
    return cfg["credentials"]["cred_ddh_project_name"]


if __name__ == '__main__':
    print('vessel_name', dds_get_json_vessel_name())
    print('aws_en', dds_get_aws_en())
    print('flag_graph_test', dds_get_flag_graph_test_mode())
    print('flag_gps_external', dds_get_flag_gps_external())
    print('flag_gps_error_forced', dds_get_flag_gps_error_forced())
    print('ls_sn_macs', dds_get_serial_number_of_macs_from_json_file())
    print('json_mac_dns', dds_get_json_mac_dns("11-22-33-44-55-66"))
    print('ft', dds_json_get_forget_time_secs())
    print('monitored_macs', dds_get_macs_from_json_file())
    print('flag_re_run', get_ddh_rerun_flag())
    print('mac_from_sn_json_file', dds_get_mac_from_sn_from_json_file('1234567'))
    print('gear_type', ddh_get_json_gear_type())
    print('check_we_have_box_env_info', dds_check_we_have_box_env_info())
    print('purge_black_macs_on_boot', dds_get_flag_ble_purge_black_macs_on_boot())
    print('purge_mac_dl_files_folder', dds_get_flag_ble_purge_this_mac_dl_files_folder())
    print('get_moving_speed', dds_get_moving_speed())
    print('dds_get_flag_rbl_en', dds_get_flag_rbl_en())
    print('dds_get_flag_sqs_en', dds_get_flag_sqs_en())
