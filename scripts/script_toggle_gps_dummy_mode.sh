#!/usr/bin/env bash


source utils.sh


echo; echo;
if [ -f "$GPS_DUMMY_MODE_FILE" ]; then
    rm "$GPS_DUMMY_MODE_FILE"
    echo 'gps dummy mode OFF'
else
    touch "$GPS_DUMMY_MODE_FILE"
    echo 'gps dummy mode ENABLED'
fi

