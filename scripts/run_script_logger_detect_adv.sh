#!/usr/bin/env bash
FOL_SCR=/home/pi/li/ddh/scripts/
VENV=/home/pi/li/venv


source $VENV/bin/activate && \
cd $FOL_SCR && \
$VENV/bin/python ./script_logger_detect_adv.py
