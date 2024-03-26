#!/usr/bin/env bash
source /home/pi/li/ddh/scripts/utils.sh


echo


# for crontab to detect already running
check_already_running "main_dds_controller"



_pb "[ RUN ] DDS | bluetooth setting UP both interfaces"
sudo hciconfig hci0 up 2> /dev/null || _py "cannot UP hci0"
sudo hciconfig hci1 up 2> /dev/null || _py "cannot UP hci1"



_pb "[ RUN ] DDS | bluetooth checking at least 1 interface OK"
(hciconfig hci0 | grep RUNNING) &> /dev/null; rv0=$?
(hciconfig hci1 | grep RUNNING) &> /dev/null; rv1=$?
if [ $rv0 -ne 0 ]; then _py "hci0 not present"; fi
if [ $rv1 -ne 0 ]; then _py "hci1 not present"; fi
if [ $rv0 -ne 0 ] && [ $rv1 -ne 0 ]; then
    _pr "error: we need at least 1 Bluetooth interface"
    exit 1
fi



_pb "[ RUN ] DDS | rfkill wlan unblock"
sudo rfkill unblock wlan



_pb "[ RUN ] DDS | set permissions 'date' and 'ifmetric'"
sudo setcap CAP_SYS_TIME+ep /bin/date
sudo setcap 'cap_net_raw,cap_net_admin+eip' /usr/sbin/ifmetric


echo && echo
_pb "###############"
_pb " DDS running   "
_pb "###############"
echo
sudo chown -R pi:pi "$FOL_DDH"
source "$FOL_VEN"/bin/activate
cd "$FOL_DDH" && "$FOL_VEN"/bin/python main_dds.py
