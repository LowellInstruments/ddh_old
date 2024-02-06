#!/usr/bin/env bash
F_VE=/home/pi/li/venv_api
F_DA=/home/pi/li/ddh


# for crontab: to detect already running
pgrep -f main_api
rv=$?
if [ $rv -eq 0 ]; then echo "DDH main_api already running"; exit 1; fi


# launch API
echo; echo 'R > calling API main python code'
source "$F_VE"/bin/activate
cd "$F_DA" && $F_VE/bin/python main_api.py
