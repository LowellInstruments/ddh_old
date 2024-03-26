#!/usr/bin/env bash
source /home/pi/li/ddh/scripts/utils.sh


echo


_pb "[ RUN ] DDH check utility"


echo && echo
_pb "###############"
_pb " CHK running   "
_pb "###############"
echo
source "$FOL_VEN"/bin/activate
cd "$FOL_DDH" && "$FOL_VEN"/bin/python main_chk.py
