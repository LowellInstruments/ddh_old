#!/usr/bin/env bash
source /home/pi/li/ddh/scripts/utils.sh


echo


# check we need a reboot
if [ -f "$LI_DDH_NEEDS_REBOOT_POST_INSTALL" ]; then
    _pr "DDH was just installed, please reboot"
    exit 0
fi



# for crontab to detect already running
check_already_running "main_ddh_controller"



_pb "DDH set XAUTHORITY, DISPLAY env. variables"
export XAUTHORITY=/home/pi/.Xauthority
export DISPLAY=:0


echo && echo
_pb "-------------"
_pb "run DDH GUI  "
_pb "-------------"
echo
sudo chown -R pi:pi "$FOL_LI"
source "$FOL_VEN"/bin/activate
cd "$FOL_DDH" && "$FOL_VEN"/bin/python main_ddh.py
