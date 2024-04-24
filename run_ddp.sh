#!/usr/bin/env bash
source /home/pi/li/ddh/scripts/utils.sh


clear
echo



echo && echo
_pb "###############"
_pb "   DDP tool    "
_pb "###############"
echo
source "$FOL_VEN"/bin/activate
cd "$FOL_DDH" && "$FOL_VEN"/bin/python main_ddp.py
