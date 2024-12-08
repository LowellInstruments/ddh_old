# Changelog

4.0.00

    2024 version of the DDH App

4.0.01 

    fixed in_ports_geo.py detection

4.0.02

    added notification field 'dl_files'

4.0.03

    added removal of mobile GPS JSON files older than 2 days

4.0.04

    bug in logs.py in building file_out on testing mode

4.0.05
    
    prevented deletion of error_maps.gif when receiving doppio maps from DDN
    added possibility of water column mode for TDO

4.0.06

    added fix for summary box DO-1 / DO-2

4.0.07

    added water column mode for graphing for DOX and TDO loggers
    added new logs.py entries, with unified timestamp
    added year filtering on AWS uploads

4.0.08

    added new maps GOM / MAB
    fixed bug setup_tab not opening after pressing "cancel without saving"
    cleaned logs generation
    made the graphs show the same order than the history

4.0.09

    Some things were not plotted for LI loggers, re-arranged water column mode

4.0.10

    Fixed command DEL using wrong filename when "testmode_" is ON.

4.0.11

    Added BRT tool to DDC and BRT compiled binary to DDH distribution.

4.0.12

    Got rid of redundant configuration file .ts_aws.txt

4.0.13

    Added fast mode for TDO loggers.
    Added new "orange tick" icon for when we do NOT rerun the logger.
    maps GIFs to .gitignore
    pop_ddh2.sh -> pop_ddh.sh

4.0.14

    fixed notification GPS error from Nick
    https://app.asana.com/0/1206361785539879/1208148157218367/f
    rearranged a bit main_gui and utils_gui.py

4.0.15

    added, and disabled, AWS_CP after each logger download
    for Lowell loggers, added scaled BAT measurement via factor

4.0.16

    improved script_ddc

4.0.17

    added notification number of GPS satellites
    modified test GPS duration from 30 -> 60 seconds
    added a condition to ignore filenames containing 'testfile_' in CST

4.0.18

    made number of satellites notification only run on "Maggie Sue"

4.0.19

    added auto detection of USB ports for Quectel shield

4.0.20

    fixed an issue with new DDH GUI watchdog

4.0.21 - September 16, 2024

    fixed checkbox value plt_outside_water
    do not plot testfile_ files

4.0.22 - September 18, 2024

    added new BLE library for DOX / TDO and [experimental] section
    script_ddc now detecting properly cell internet on issues 'i'

4.0.23 - September 19, 2024

    fixed some bug in BLE_LSB_DOX
    added notification when cannot clock sync at boot

4.0.24 - September 23, 2024

    fixed logic bug plot-in-water, out-of-water

4.0.25 - September 25, 2024

    improved code readability on DDH, not MAT

4.0.26 - September 25, 2024

    had to add _lock_icon(0) on utils_gui, STATE_DDS_BLE_HARDWARE_ERROR

4.0.27 - September 26, 2024

    new strategy to not send so many BLE hardware errors via e-mail
    disabled CRC on TDO logger downloads per default

4.0.28 - September 27, 2024

    done better CST, less logs

4.0.29 - October 1, 2024

    reduced printed logs a lot
    added some direct SNS alarm notifications (no SQS) to API if this crashes
    added API controller process to API

4.0.30 - October 3, 2024

    graphing ALL data is the new default, before it was only IN-WATER data

4.0.31 - October 7, 2024

    forcing AWS sync even if number of files = 0 so API is refreshed
    better obtaining ICCID when executing run_dds.sh

4.0.32 - October 16, 2024

    dynamic reconfiguration TDO / DOX on config.toml experimental conf_tdo and conf_dox

4.0.33 - October 20, 2024

    slightly better main_controller_api

4.0.34 - October 22, 2024

    added error when no plotting because only testfiles_ are present

4.0.35 - November 12, 2024

    new buttons strategy in file dds/buttons.py

4.0.36 - November 14, 2024

    improved buttons strategy in file dds/buttons.py
    improved AWS cp vs sync
    added better condition on DO2 when changing DRI

4.0.37 - November 14, 2024

    removed the e) edit BLE range tool option from DDC

4.0.38 - November 15, 2024

    moved GPQ file generation to generate smaller files

4.0.39 - November 16, 2024

    disabled CST_serve in main_dds.py

4.0.40 - November 16, 2024

    DOX loggers, better logic for "need for DOX interval reconfiguration"

4.0.41 - November 16, 2024

    improved GPQ file generation to remove warning

4.0.42 - November 18, 2024

    DDC new checks it can connect to AWS
    bug: AWS_CP better cloud icon update, it stayed just "busy"

4.0.43 - November 18, 2024

    better ways to detect process running

4.0.44 - November 22, 2024

    hardcoded DHU="00050" in TDO deploy script

4.0.45 - November 24, 2024

    new LOCAL API main_dda for features such as smart lock out time

4.0.46 - December 8, 2024

    moved SCC 00050 in script_deploy_logger_tdo_utils.py

