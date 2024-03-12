#!/usr/bin/env bash


source utils.sh


echo; echo;
if [ -f "$GROUPED_S3_FILE_FLAG" ]; then
    rm "$GROUPED_S3_FILE_FLAG"
    echo 'box does AWS grouped sync'
else
    touch "$GROUPED_S3_FILE_FLAG"
    echo 'box does traditional MAC address AWS sync'
fi

