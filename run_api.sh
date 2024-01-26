#!/usr/bin/env bash
F_VE=/home/pi/li/venv_api
F_DA=/home/pi/li/ddh


# for crontab: to detect already running
ps -aux | grep "main_api_controller" | grep -v grep
ALREADY=$?
if [ "$ALREADY" -eq 0 ]; then echo "API already running in bash, leaving"; exit 0; fi


# launch API
echo; echo 'R > calling API main python code'
source "$F_VE"/bin/activate
cd "$F_DA" && $F_VE/bin/python main_api.py
