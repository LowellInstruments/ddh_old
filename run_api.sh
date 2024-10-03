#!/usr/bin/env bash
source /home/pi/li/ddh/scripts/utils.sh


clear

# for crontab to detect already running
check_already_running "main_api_controller"
check_already_running "requirements_api"


echo && echo
_pb "###############"
_pb "     DDH API   "
_pb "###############"
echo
sudo chown -R pi:pi "$FOL_LI"
source "$FOL_VAN"/bin/activate
pip install --no-cache-dir "$FOL_DDT"/_dt_files/my_wheels/botocore-1.29.165-py3-none-any.whl
pip install -r "$FOL_DDH"/requirements_api.txt
cd "$FOL_DDH" && "$FOL_VAN"/bin/python main_api.py
