#!/usr/bin/env bash
source /home/pi/li/ddh/scripts/utils.sh


echo



_pb "[ RUN ] LXP | set XAUTHORITY and DISPLAY environment variables"
export XAUTHORITY=/home/pi/.Xauthority
export DISPLAY=:0


echo && echo
_pb "###############"
_pb "     DDH LXP   "
_pb "###############"
echo
python main_lxp.py
