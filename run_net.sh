#!/usr/bin/env bash
source /home/pi/li/ddh/scripts/utils.sh


echo



echo && echo
_pb "###############"
_pb "     DDH NET   "
_pb "###############"
echo
cd "$FOL_DDH" && python main_net.py
