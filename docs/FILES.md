# Files in /home/pi/li

Files more global than DDH ones, so it is useful they survive a wipe of the ``ddh`` folder.

### .ddt_cell_shield.flag

The presence of this file indicates the DDH uses the cell shield hardware.

### .ddt_sailor_shield.flag

The presence of this field indicates the DDH uses the power shield sailor-hat hardware.

### .ddt_this_box_has_grouped_s3_uplink.flag

Means the DDH uploads its file to AWS S3 in a grouped structure.

### .ddt_gps_external.flag

Means the DDH uses a GPS puck to get its GPS position instead of the cell shield.

### .ddt_j4h_shield.flag

The presence of this field indicates the DDH uses the power shield juiceforhalt hardware.

### .fw_cell_ver

Contains the firmware version of the cell shield. Populated when DDH GUI runs.

### .iccid

Contains the ID of the SIM of the cell shield. Populated when DDH GUI runs.

### .ddh_test_mode.flag

Sends files to AWS with the ``testfile`` filename prefix for easy identification of test runs. Set by using ``DDC`` tool.

### .gps_quectel_at_usb4'

If present, indicates the cell shield does not operate on USB2 but USB4. Created by ``run_dds.sh``.





# Files in /home/pi/li/ddh

While operating, the DDH relies on a series of files to indicate flags, configuration, temporary states, small databases, etc.

This page lists some of them for development purposes or simply understanding of the code.

### db/db_his.json

Small database for the table in the history tab. Requires package ``strip.pysondb`` which is a very small and fast database.

### db/db_status.json

Contains the result of the last interaction the DDH had with AWS S3 and SQS.

### gui/res/*.gif

Daily forecast maps downloaded from DDN / Lightsail.

### .ddh_version

Contains the version number of the DDH software.

### .ddh_plt_outside_water

When present, the DDH graph tab plots even logger data outside the water.

### .ts_aws.txt

Contains the last timestamp of attempt to AWS S3. Seems redundant with db_status.json?

### dl_files/<mac>

Contains several files either downloaded or automatically generated from them.
- LID: data binary file.
- CSV: data CSV file.
- GPS: information downloaded from logger.
- CST: data + GPS tracking file. Automatically generated with GPQ engine (see below).

FMG and SMG files work in conjunction with the file ``.ddh_plt_ouside_water`` and allow for the graph tab to show data out of the water or discard it.
- FMG: fast mode graph. If present, means this file has profiling (fast recording rate) data.
- SMG: slow mode graph. If present, means this file has NOT profiling data. This file helps not plotting data outside the water.

### dl_files/ddh#nameoftheboat

Contains the TRACKING log of the vessel. When something interesting happens at a GPS position, the content of a LEF file is concatenated to one line in this file.

### dds/gpq

This contains a small database of GPS positions for the last few days. Contains 2 types of JSON files:
- fixed_filename.json: fixed hauls, helps in generating a CST file with 1 repeated location.
- mobile_date.json: mobile hauls, helps in generating a CST file with N different locations to reconstruct GPS path of trawl.

### dds/lef

Stands for Lowell Event File. Files here are created when a download event happens. This info is attached to the TRACKING log to synchronize time / event happened / position for ODN.

### dds/macs

Stores black and orange temporary excluded macs

### dds/sqs

Contains notification files not yet sent uplink via SQS.

### dds/tweak

Contains files such as ``11-22-33-44-55-66.rst``. If this file is present, the next time DDH encounters this logger MAC, it will send the RST command to make the logger restart itself.

### logs

DDH running logs.

### rpc

I don't think we will ever use the RPC version of this. So much work. But, meh, leave it there.

### settings/rerun_flag.toml

Stores the ``advanced`` tab configuration setting to re-run logger after being downloaded or not.

### settings/language.toml

Indicates the language the DDH should display its text with. Under development.

### settings/all_macs.toml

Contains all the MACs of the project the DDH is part of.

### settings/config.toml

Contains the configuration of the running DDH. May contain all the MACs in ``all_macs.toml`` or a subset of them.




# Files in /tmp

These fields only last while the DDH is on and get eliminated upon reboot. They are useful to indicate temporary flags.

### .ddh_needs_reboot_post_install.flag

DDH GUI application will not boot while this field is present.

### gps_dummy_mode.json

DDH simulates latitude and longitude values specified in ``config.toml``.

### ddh_boat_speed.json

When present, DDH simulates speed.

### ddh_disabled_ble_file.flag

When present, the DDH does NOT scan for Bluetooth loggers.

### ddh_graph_test_mode.json

When present, DDH graphs test data, not real one. Toggled with ``DDC`` tool.

### graph_req.json 

Written by DDS to indicate DDH GUI the logger it wants a plot for.

### gps_last.json

Contains the last GPS position of the DDH. Used by API.

### ble_iface_used.json

Written by DDS to tell which BLE interface is being used, internal or external.

### gui_closed.flag

Indicates the DDH GUI has been closed pressing the upper-right ``X``.

### ddh_aws_has_something_to_do_via_gui.flag

Useful to indicate from the GUI we want to force an AWS sync.

### ddh_cnv_requested_via_gui.flag

Useful to indicate from the GUI we want to force a LID conversion process.

### ddh_got_update_file.flag

Indicates the DDH updated itself recently (beta).

### ddh_app_override_file.flag

Indicates the "clear lock out" button has been pressed to clear macs, force a download, etc.
