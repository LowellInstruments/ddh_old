#!/usr/bin/env bash
source /home/pi/li/ddh/scripts/utils.sh


clear
echo



echo && echo
_pb "###############"
_pb "   DDB API    "
_pb "###############"
echo
source "$FOL_VBN"/bin/activate
cd "$FOL_DDH" && "$FOL_VBN"/bin/python "$FOL_LI"/ddb/main_ddb.py
