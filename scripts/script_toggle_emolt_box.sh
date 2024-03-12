#!/usr/bin/env bash


source utils.sh


echo; echo;
if [ -f "$EMOLT_FILE_FLAG" ]; then
    rm "$EMOLT_FILE_FLAG"
    echo 'box marked as DDH'
else
    touch "$EMOLT_FILE_FLAG"
    echo 'box marked as emolt-ddh'
fi

