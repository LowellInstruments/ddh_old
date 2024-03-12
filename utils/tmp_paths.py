# when present, DDH simulates latitude and longitude values from config.toml
TMP_PATH_GPS_DUMMY = "/tmp/gps_dummy_mode.json"

# when present, DDH simulates speed
TMP_PATH_DDH_BOAT_SPEED_JSON = "/tmp/ddh_boat_speed.json"

# when present, the BLE code on the DDH is disabled
TMP_PATH_DISABLE_BLE = "/tmp/ddh_disabled_ble_file.flag"

# written by real GPS to know the last GPS position
TMP_PATH_GPS_LAST_JSON = "/tmp/gps_last.json"

# indicates the DDH GUI has been closed pressing the upper-right X
TMP_PATH_GUI_CLOSED_FLAG = "/tmp/gui_closed.flag"

# indicates the DDH GUI wants to force an AWS sync
TMP_PATH_AWS_HAS_WORK_VIA_GUI = "/tmp/ddh_aws_has_something_to_do_via_gui.flag"

# indicates the DDH GUI updated itself (beta)
TMP_PATH_DDH_GOT_UPDATE = "/tmp/ddh_got_update_file.flag"

# indicates the "clear lock out" button has been pressed
# this clears macs, forces a download, etc.
TMP_PATH_DDH_APP_OVERRIDE = "/tmp/ddh_app_override_file.flag"
