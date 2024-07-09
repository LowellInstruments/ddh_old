#!/usr/bin/env bash
source /home/pi/li/ddh/scripts/utils.sh


clear

# for crontab to detect already running
check_already_running "main_api"


echo && echo
_pb "###############"
_pb "     DDH API   "
_pb "###############"
echo
sudo chown -R pi:pi "$FOL_LI"
source "$FOL_VAN"/bin/activate
pip install -r requirements.api.txt
cd "$FOL_DDH" && "$FOL_VAN"/bin/python main_api.py
