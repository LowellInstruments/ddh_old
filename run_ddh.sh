#!/usr/bin/env bash
F_LI=/home/pi/li
F_DA="$F_LI"/ddh
F_VE=/home/pi/li/venv


# for crontab: to detect already running
ps -aux | grep "main_ddh_controller" | grep -v grep
ALREADY=$?
if [ "$ALREADY" -eq 0 ]; then echo "DDH already running in bash, leaving"; exit 0; fi


# abort upon any error
set -e
trap 'echo "$BASH_COMMAND" TRAPPED! rv $?; cd $F_DA' EXIT


# needed for crontab to access the X-window system
export XAUTHORITY=/home/pi/.Xauthority
export DISPLAY=:0


echo; echo 'R > calling DDH GUI main python code'
sudo chown -R pi:pi "$F_LI"
source "$F_VE"/bin/activate
cd "$F_DA" && $F_VE/bin/python main_ddh.py
