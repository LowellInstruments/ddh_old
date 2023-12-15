import toml
import os


PATH_FILE_CFG = 'settings/config.toml'
ALT_PATH_FILE_CFG = '../settings/config.toml'


class DdhCfg:

    def __init__(self):


    @staticmethod
    def _cfg_check_file_integrity(p=PATH_FILE_CFG):
        try:
            with open(p, 'r') as f:
                toml.load(f)
        except (Exception, ) as ex:
            print('error: toml_cfg_check_file_integrity: ', ex)

    @staticmethod
    def cfg_load(p=PATH_FILE_CFG):
        try:
            DdhCfg._cfg_check_file_integrity(p)
            with open(p, 'r') as f:
                global _c
                _c = toml.load(f)
        except (Exception, ) as ex:
            print('error: toml_cfg_read_file: ', ex)
            os._exit(1)

    @staticmethod
    def cfg_save(c, p=PATH_FILE_CFG):
        try:
            DdhCfg._cfg_check_file_integrity(p)
            with open(p, 'w') as f:
                return toml.dump(c, f)
        except (Exception, ) as ex:
            print('error: toml_cfg_read_file: ', ex)
            os._exit(1)


    def dds_get_json_vessel_name():
        return _c['behavior']['ship_name']


    def dds_get_aws_en():
        return _c['flags']['aws_en']


    def dds_get_flag_graph_test_mode():
        return _c['flags']['hook_graph_test_mode']


    def dds_get_flag_gps_external():
        return _c['flags']['g_gps_is_external']


    def dds_get_flag_gps_error_forced():
        return _c['flags']['hook_gps_error_measurement_forced']


    def dds_get_serial_number_of_macs_from_json_file():
        return list(_c['monitored_macs'].values())


    def dds_get_macs_from_json_file():
        return list(_c['monitored_macs'].keys())


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

        return _c['monitored_macs'][mac]


    def dds_json_get_forget_time_secs():
        return int(_c['behavior']['forget_time'])


    def dds_get_monitored_macs():
        return _c['monitored_macs']


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

        for k, v in _c['monitored_macs'].items():
            if v.lower() == sn.lower():
                return k.lower()
        return None


    def dds_get_flag_rerun():
        return _c['flags']['rerun_logger']


    def ddh_get_json_gear_type():
        return _c['behavior']['gear_type']


    def dds_check_we_have_box_env_info():
        sn = _c['credentials']['cred_ddh_serial_number']
        if not sn:
            print('error: need box sn')
            os._exit(1)
        prj = _c['credentials']['cred_ddh_project_name']
        if not prj:
            print('error: need box project name')
            os._exit(1)


    def dds_get_flag_ble_purge_black_macs_on_boot():
        return _c['flags']['hook_ble_purge_black_macs_on_boot']


    def dds_get_flag_ble_purge_this_mac_dl_files_folder():
        return _c['flags']['hook_ble_purge_this_mac_dl_files_folder']


    def dds_get_moving_speed():
        return _c['behavior']['moving_speed']


    def dds_get_flag_ble_en():
        return _c['flags']['ble_en']


    def dds_ble_set_cc26x2r_recipe_flags_to_file(p=PATH_FILE_CFG):
        global _c
        flag = _c['flags']['rerun_logger']
        flag ^= 1
        _c['flags']['rerun_logger'] = flag
        cfg_save(_c, p)
        # reload!
        cfg_load(p)
        return flag


if __name__ == '__main__':
    # for a test, we alter the path
    cfg_load(ALT_PATH_FILE_CFG)
    print('vessel_name', dds_get_json_vessel_name())
    print('aws_en', dds_get_aws_en())
    print('flag_graph_test', dds_get_flag_graph_test_mode())
    print('flag_gps_external', dds_get_flag_gps_external())
    print('flag_gps_error_forced', dds_get_flag_gps_error_forced())
    print('ls_sn_macs', dds_get_serial_number_of_macs_from_json_file())
    print('json_mac_dns', dds_get_json_mac_dns("11-22-33-44-55-66"))
    print('ft', dds_json_get_forget_time_secs())
    print('monitored_macs', dds_get_monitored_macs())
    print('flag_re_run', dds_get_flag_rerun())
    print('mac_from_sn_json_file', dds_get_mac_from_sn_from_json_file('1234567'))
    print('gear_type', ddh_get_json_gear_type())
    print('check_we_have_box_env_info', dds_check_we_have_box_env_info())
    print('purge_black_macs_on_boot', dds_get_flag_ble_purge_black_macs_on_boot())
    print('purge_mac_dl_files_folder', dds_get_flag_ble_purge_this_mac_dl_files_folder())
    print('get_moving_speed', dds_get_moving_speed())
    print('toggle_rerun', dds_ble_set_cc26x2r_recipe_flags_to_file(ALT_PATH_FILE_CFG))
