folder ~li
==========

Files more global than DDH ones, they survive a wipe of the ``ddh`` folder.

### .ddt_cell_shield.flag

Indicates the DDH uses cell shield hardware.

### .ddt_j4h_shield.flag

Indicates the DDH uses the power shield juiceforhalt hardware.

### .ddt_sailor_shield.flag

The presence of this field indicates the DDH uses the power shield sailor-hat hardware.

### .ddt_this_box_has_grouped_s3_uplink.flag

DDH uploads its file to AWS S3 in a grouped structure.

### .ddt_gps_external.flag

DDH uses a GPS puck to get its GPS position instead of the cell shield.

### .fw_cell_ver

Contains the firmware version of the cell shield. Populated when DDH python code runs.

### .iccid

Contains the ID of the SIM of the cell shield. Populated by ``run_dds.sh``.

### .ddh_test_mode.flag

Sends files to AWS with the ``testfile`` filename prefix for easy identification of test runs. 

Set by using ``DDC`` tool.




folder ~li/ddh
===============

DDH application's flags, configuration, temporary states, small databases, etc.

This page lists some of them for development purposes or simply understanding of the code.

### db/db_his.json

Small database for history tab. Requires package ``strip.pysondb``.

### db/db_status.json

Contains the result of last interaction with AWS S3 and SQS.

### gui/res/*_dtm.gif, *_gom.gif, *_mab.gif

Daily forecast maps downloaded from DDN / Lightsail.

### .ddh_version

Contains the version number of the DDH software.

### .ddh_plt_outside_water

When present, the DDH graph tab plots all logger data, not only the one inside the water.

### dl_files/<mac>

Contains several files either downloaded or automatically generated from them.
- LID: data binary file.
- CSV: data CSV file.
- GPS: location information downloaded from logger.
- CST: data + GPS tracking file. Automatically generated with GPQ engine (see below).

FMG and SMG files work in conjunction with the file ``.ddh_plt_ouside_water``.
- FMG: fast mode graph. This file has profiling (fast recording rate) data.
- SMG: slow mode graph. This file has NOT profiling data, so it won't show when plotting only inside-water.

### dds/lef

Stands for Lowell Event File. Created when a logger download event happens. 

This info is attached to the vessel TRACKING log (next) to synchronize time / event happened / position for ODN.

### dl_files/ddh#nameoftheboat

Contains the TRACKING log of the vessel. Some lines can have concatenated a LEF event after symbol ``***``.

### dds/gpq

This contains a small database of GPS positions for the last few days. Contains 2 types of JSON files:
- fixed_filename.json: fixed hauls, helps in generating a CST file with 1 repeated location.
- mobile_date.json: mobile hauls, helps in generating a CST file with N different locations to reconstruct GPS path of trawl.


### dds/macs

Black and orange temporary excluded macs.

### dds/sqs

Contains notification files not yet sent uplink via SQS. Deleted once sent.

### dds/tweak

Contains files such as ``11-22-33-44-55-66.rst``. 

If present, the next time DDH encounters this logger MAC, it will restart the logger.

Solves some old bugs.

### logs

DDH application logs, contains python messages.

### rpc

I don't think we will ever use the RPC version of this. So much work. But, meh, leave it there.

### settings/rerun_flag.toml

Stores the ``advanced`` tab configuration setting to re-run logger after being downloaded or not.

### settings/language.toml

Indicates the language the DDH should display its text with. Under development.

### settings/all_macs.toml

Contains all the logger MACs of the 3-letters project name this current DDH is part of.

### settings/config.toml

DDH main configuration file. May contain all the MACs in ``all_macs.toml`` or a subset of them.




folder /tmp
===========

These fields only last while the DDH is on.

They get eliminated upon reboot. They are useful to indicate temporary expiring flags.

### .ddh_needs_reboot_post_install.flag

DDH GUI application will not boot while this field is present.

### gps_dummy_mode.json

This flag indicates the DDH it should use the simulated latitude and longitude values specified in ``config.toml``.

### ddh_boat_speed.json

When present, DDH simulates speed.

### ddh_disabled_ble_file.flag

When present, the DDH does NOT scan for Bluetooth loggers.

### ddh_graph_test_mode.json

When present, DDH graphs display test data, not real one. Toggled with ``DDC`` tool.

### graph_req.json 

Written by DDS to indicate DDH GUI a logger it wants a plot for. Used after a logger download.

### gps_last.json

Contains the last GPS position of the DDH. Used by API.

### ble_iface_used.json

Written by DDS to tell which BLE interface is being used, internal or external.

### gui_closed.flag

Indicates the DDH GUI has been closed pressing the upper-right ``X``.

### ddh_aws_has_something_to_do_via_gui.flag

Useful to indicate from the GUI we want to force an AWS sync. The user may have pressed the cloud icon.

### ddh_cnv_requested_via_gui.flag

Useful to indicate from the GUI we want to force a LID conversion process.

### ddh_got_update_file.flag

Indicates the DDH updated itself recently (beta).

### ddh_app_override_file.flag

Indicates the ``clear lock out`` button has been pressed to clear macs, force a download, etc.

### internet_via.json

Indicates the last used internet via (cell or wlan or none).
