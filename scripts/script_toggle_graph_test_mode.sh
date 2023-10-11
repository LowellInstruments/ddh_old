#!/usr/bin/env bash


# script called by DDU-text utility, not used by DDU-gui

FILE_GRAPH_TEST_MODE='/tmp/ddh_graph_test_mode.json'

echo; echo;
if [ -f "$FILE_GRAPH_TEST_MODE" ]; then
    rm "$FILE_GRAPH_TEST_MODE"
    echo 'graph test mode OFF'
else
    touch "$FILE_GRAPH_TEST_MODE"
    echo 'graph test mode ON'
fi

