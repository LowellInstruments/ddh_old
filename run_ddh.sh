#!/usr/bin/env bash
F_LI=/home/pi/li
F_DA="$F_LI"/ddh
F_VE=/home/pi/li/venv


clear
source $F_AU/utils.sh
echo

# for crontab to detect already running
check_already_running "main_ddh_controller"


_pb "[ RUN ] DDH | setting XAUTHORITY and DISPLAY environment variables"
export XAUTHORITY=/home/pi/.Xauthority
export DISPLAY=:0


echo && echo
_pb "###############"
_pb "     DDH GUI   "
_pb "###############"
echo
sudo chown -R pi:pi "$F_LI"
source "$F_VE"/bin/activate
cd "$F_DA" && $F_VE/bin/python main_ddh.py
