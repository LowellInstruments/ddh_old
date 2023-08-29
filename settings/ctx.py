import asyncio
from dds.emolt import ddh_is_emolt_box, ddh_is_dev_platform
from utils.ddh_shared import send_ddh_udp_gui


# to send updates to GUI
_u = send_ddh_udp_gui


# plot stuff
g_p_d = ""
g_p_ax = None
g_p_ts = ""
g_p_met = []
plt_units_temp = None
plt_units_depth = None
span_dict = None


# AWS / SQS enabled or not
aws_en = True
sqs_en = True


# BLE: enabled or not + switch capability
ble_en = True
sw_ble_en = True
ble_rfkill = False


# rockblocks: enabled or not
rbl_en = False


# GPS configuration
g_gps_is_external = False


# debug hooks :)
hook_gps_dummy_measurement = ddh_is_dev_platform()
hook_gps_error_measurement_forced = False
hook_ble_purge_black_macs_on_boot = False
hook_ble_purge_this_mac_dl_files_folder = False
hook_ble_scan_cc26x2r_sim = False


# for asynchronous Bleak BLE
ael = asyncio.get_event_loop()


class BLEAppException(Exception):
    pass
