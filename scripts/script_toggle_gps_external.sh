#!/usr/bin/env bash


source utils.sh


echo; echo;
if [ -f "$GPS_EXTERNAL_FILE_FLAG" ]; then
    rm "$GPS_EXTERNAL_FILE_FLAG"
    echo 'box will use internal GPS'
else
    touch "$GPS_EXTERNAL_FILE_FLAG"
    echo 'box will use external GPS'
fi

