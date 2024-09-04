#!/usr/bin/env bash
source /home/pi/li/ddh/scripts/utils.sh


echo


# check we need a reboot
if [ -f "$LI_DDH_NEEDS_REBOOT_POST_INSTALL" ]; then
    _pr "DDS was just installed, please reboot"
    exit 0
fi


# for crontab to detect already running
check_already_running "main_dds_controller"



# detect cell shield SIM ID
rm "$LI_FILE_ICCID" > /dev/null 2>&1
rm "$LI_PATH_DDH_GPS_CELL_SHIELD_USB4" > /dev/null 2>&1
QUECTEL_VID_PID=2c7c:0125
which_ports_has_vid_pid $QUECTEL_VID_PID | grep /dev/ttyUSB4
rv=$?
if [ "$rv" -eq 0 ]; then
    _pb "DDS query Quectel cell shield for SIM ID on /dev/ttyUSB4"
    echo -ne "AT+QCCID\r" > /dev/ttyUSB4 && \
    sleep 0.1 && timeout 1 cat -v < /dev/ttyUSB4 | grep QCCID > "$LI_FILE_ICCID"
    touch "$LI_PATH_DDH_GPS_CELL_SHIELD_USB4"
else
    which_ports_has_vid_pid $QUECTEL_VID_PID | grep /dev/ttyUSB2
    rv=$?
    if [ "$rv" -eq 0 ]; then
        _pb "DDS query Quectel cell shield for SIM ID on /dev/ttyUSB2"
        echo -ne "AT+QCCID\r" > /dev/ttyUSB2 && \
        sleep 0.1 && timeout 1 cat -v < /dev/ttyUSB2 | grep QCCID > "$LI_FILE_ICCID"
    fi
fi



_pb "DDS set BLE interfaces UP"
sudo hciconfig hci0 up 2> /dev/null || _py "cannot UP hci0"
sudo hciconfig hci1 up 2> /dev/null || _py "cannot UP hci1"



_pb "DDS check at least 1 BLE interface OK"
(hciconfig hci0 | grep RUNNING) &> /dev/null; rv0=$?
(hciconfig hci1 | grep RUNNING) &> /dev/null; rv1=$?
if [ $rv0 -ne 0 ]; then _py "hci0 not present"; fi
if [ $rv1 -ne 0 ]; then _py "hci1 not present"; fi
if [ $rv0 -ne 0 ] && [ $rv1 -ne 0 ]; then
    _pr "error: DDS needs at least 1 Bluetooth interface"
    exit 1
fi



_pb "DDS check wi-fi interface is not rf-killed"
sudo rfkill unblock wlan



_pb "DDS set permissions 'date' and 'ifmetric'"
sudo setcap CAP_SYS_TIME+ep /bin/date
sudo setcap 'cap_net_raw,cap_net_admin+eip' /usr/sbin/ifmetric



echo && echo
_pb "-------------"
_pb "run DDS core "
_pb "-------------"
echo
sudo chown -R pi:pi "$FOL_DDH"
source "$FOL_VEN"/bin/activate
cd "$FOL_DDH" && "$FOL_VEN"/bin/python main_dds.py
