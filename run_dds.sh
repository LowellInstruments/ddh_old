#!/usr/bin/env bash
source /home/pi/li/ddh/scripts/utils.sh


echo


# check we need a reboot
if [ -f "$LI_DDH_NEEDS_REBOOT_POST_INSTALL" ]; then
    _pr "[ RUN ] DDS | you just installed, please reboot"
    exit 0
fi


# for crontab to detect already running
check_already_running "main_dds_controller"


# detect cell shield SIM ID
rm "$LI_FILE_ICCID" > /dev/null 2>&1
rm "$LI_PATH_DDH_GPS_CELL_SHIELD_USB4" > /dev/null 2>&1
lsusb | grep Quectel
rv=$?
if [ "$rv" -eq 0 ]; then
    _pb "[ RUN ] DDS | capturing quectel cell shield SIM ID"
    # rare occasions where quectel cell USB control port is at ttyUSB4
    ls /dev/ttyUSB4 > /dev/null 2>&1
    rv=$?
    if [ "$rv" -eq 0 ]; then
        echo -ne "AT+QCCID\r" > /dev/ttyUSB4 && \
        sleep 0.1 && timeout 1 cat -v < /dev/ttyUSB4 > "$LI_FILE_ICCID"
        touch "$LI_PATH_DDH_GPS_CELL_SHIELD_USB4"
    else
      # usually, quectel cell USB control port is at ttyUSB2
        ls /dev/ttyUSB2 > /dev/null 2>&1
        rv=$?
        if [ "$rv" -eq 0 ]; then
            echo -ne "AT+QCCID\r" > /dev/ttyUSB2 && \
            sleep 0.1 && timeout 1 cat -v < /dev/ttyUSB2 > "$LI_FILE_ICCID"
        fi
    fi
fi



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
