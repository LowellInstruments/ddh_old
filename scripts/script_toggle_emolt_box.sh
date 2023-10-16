#!/usr/bin/env bash


# script called by DDU-text utility, not used by DDU-gui

EMOLT_FILE_FLAG=/home/pi/li/.ddt_this_is_emolt_box.flag

echo; echo;
if [ -f "$EMOLT_FILE_FLAG" ]; then
    rm "$EMOLT_FILE_FLAG"
    echo 'box marked as DDH'
else
    touch "$EMOLT_FILE_FLAG"
    echo 'box marked as emolt-ddh'
fi

