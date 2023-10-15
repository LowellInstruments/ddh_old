#!/usr/bin/env bash


# script called by DDU-text utility, not used by DDU-gui

GROUPED_S3_FILE_FLAG=/home/pi/li/.ddt_this_box_has_grouped_s3_uplink.flag

echo; echo;
if [ -f "$GROUPED_S3_FILE_FLAG" ]; then
    rm "$GROUPED_S3_FILE_FLAG"
    echo 'box does AWS grouped sync'
else
    touch "$GROUPED_S3_FILE_FLAG"
    echo 'box does traditional MAC address AWS sync'
fi

