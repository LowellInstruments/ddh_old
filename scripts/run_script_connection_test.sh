#!/usr/bin/env bash
FOL_SCR=/home/pi/li/ddh/scripts/
VENV=/home/pi/li/venv


clear
echo; echo; echo
echo '----------------------------------------------------------------------------------'
echo 'DDH CONNECTION TEST SCRIPT -> in progress'
source $VENV/bin/activate && cd $FOL_SCR && $VENV/bin/python ./script_connection_test.py
echo '----------------------------------------------------------------------------------'
