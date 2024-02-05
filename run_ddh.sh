#!/usr/bin/env bash
source /home/pi/li/ddh/utils.sh



clear
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
source "$FOL_VEN"/bin/activate
cd "$FOL_DDH" && "$FOL_VEN"/bin/python main_ddh.py
