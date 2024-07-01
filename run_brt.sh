#!/usr/bin/env bash
source /home/pi/li/ddh/scripts/utils.sh


clear

check_already_running "main_brt"


echo && echo
_pb "###############"
_pb "     DDH BRT   "
_pb "###############"
echo

cp "$FOL_LI"/brt/main_brt.py "$FOL_DDH"

source "$FOL_VEN"/bin/activate
cd "$FOL_DDH" && "$FOL_VEN"/bin/python main_brt.py
