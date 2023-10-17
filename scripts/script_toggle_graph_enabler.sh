#!/usr/bin/env bash


# script called by DDU-text utility, not used by DDU-gui

FILE_GRAPH_ENABLER='/home/pi/.ddh_graph_enabler.json'

echo; echo;
if [ -f "$FILE_GRAPH_ENABLER" ]; then
    rm "$FILE_GRAPH_ENABLER"
    echo 'graph enabler file removed'
else
    touch "$FILE_GRAPH_ENABLER"
    echo 'graph enabler file ON'
fi

