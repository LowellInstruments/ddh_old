#!/usr/bin/env bash


# script called by DDU-text utility, not used by DDU-gui

GPS_DUMMY_MODE_FILE=/tmp/gps_dummy_mode.json

echo; echo;
if [ -f "$GPS_DUMMY_MODE_FILE" ]; then
    rm "$GPS_DUMMY_MODE_FILE"
    echo 'gps dummy mode OFF'
else
    touch "$GPS_DUMMY_MODE_FILE"
    echo 'gps dummy mode ENABLED'
fi

