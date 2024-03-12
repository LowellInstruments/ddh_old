#!/usr/bin/env bash


source utils.sh


echo; echo;
if [ -f "$FILE_GRAPH_TEST_MODE" ]; then
    rm "$FILE_GRAPH_TEST_MODE"
    echo 'graph test mode OFF'
else
    touch "$FILE_GRAPH_TEST_MODE"
    echo 'graph test mode ENABLED'
fi

