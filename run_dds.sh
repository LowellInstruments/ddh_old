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



_pb "DDS activating virtualenv"
sudo chown -R pi:pi "$FOL_DDH"
source "$FOL_VEN"/bin/activate


_pb "DDS running main_qus.py"
cd "$FOL_DDH" && "$FOL_VEN"/bin/python main_qus.py



# detect cell shield SIM ID and write it to file
_pb "DDS query Quectel cell shield for SIM ID on $QUECTEL_USB_CTL"
rm "$LI_FILE_ICCID" > /dev/null 2>&1
QUECTEL_USB_CTL=$(cat /tmp/usb_quectel_ctl)
echo -ne "AT+QCCID\r" > $QUECTEL_USB_CTL && \
sleep 0.1 && timeout 1 cat -v < $QUECTEL_USB_CTL | grep QCCID > "$LI_FILE_ICCID"




echo && echo
_pb "-------------"
_pb "run DDS core "
_pb "-------------"
echo
cd "$FOL_DDH" && "$FOL_VEN"/bin/python main_dds.py
