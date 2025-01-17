#!/usr/bin/env bash
source /home/pi/li/ddh/scripts/utils.sh


echo


# check we need a reboot
if [ -f "$LI_DDH_NEEDS_REBOOT_POST_INSTALL" ]; then
    _pr "DDS was just installed, please reboot"
    exit 0
fi



# install APT things that we will need
dpkg -s python3-pyqt5.qtwebkit | grep "Status: install ok"
rv=$?
if [ $rv -ne 0 ]; then
    _pb "installing via APT -> python3-pyqt5.qtwebkit"
    sudo apt-get install -y python3-pyqt5.qtwebkit
    sudo apt remove modemmanager
fi


# tweaking python files for PyQtWeb*Widgets
echo 'tweaking designer_main.py depending on laptop vs. raspberry'
sed -i 's/from PyQt5 import QtWebEngineWidgets/from PyQt5 import QtWebKitWidgets/g' designer_main.py
sed -i 's/self.webView = QtWebEngineWidgets.QWebEngineView(self.tab_trawls)/self.webView = QtWebKitWidgets.QWebView(self.tab_trawls)/g' designer_main.py


# for crontab to detect already running
check_already_running "main_dds_controller"



# start with a clean BLE sheet
_pb "DDS delete BLE cache"
grep 'ble_del_cache = 1' "$FOL_DDH"/settings/config.toml
rv=$?
if [ $rv -eq 0 ]; then
    _pb "* EXP * removing cache from /etc/bluetooth/main.conf"
    LS_HCI_MACS=$(hciconfig -a | grep "BD Address" | cut -d " " -f 3)
    for HM in $LS_HCI_MACS; do sudo rm "/var/lib/bluetooth/$HM"/cache/*; done
    sudo sed -i '/#Cache = always/c\Cache = no' /etc/bluetooth/main.conf
    sudo systemctl restart bluetooth
    sleep 1
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



_pb "DDS set BLE connection supervision timeout"
touch /tmp/200
echo '200' | sudo tee /sys/kernel/debug/bluetooth/hci0/supervision_timeout 2> /dev/null
echo '200' | sudo tee /sys/kernel/debug/bluetooth/hci1/supervision_timeout 2> /dev/null



_pb "DDS check wi-fi interface is not rf-killed"
sudo rfkill unblock wlan



_pb "DDS set permissions on linux binaries 'date' and 'ifmetric'"
sudo setcap CAP_SYS_TIME+ep /bin/date
sudo setcap 'cap_net_raw,cap_net_admin+eip' /usr/sbin/ifmetric



_pb "DDS activating virtualenv"
sudo chown -R pi:pi "$FOL_DDH"
source "$FOL_VEN"/bin/activate



_pb "DDS run main_qus.py to auto-detect Quectel shield USB ports"
cd "$FOL_DDH" && "$FOL_VEN"/bin/python main_qus.py
QUECTEL_USB_CTL=$(cat /tmp/usb_quectel_ctl)



# detect cell shield SIM ID and write it to file
if [ "${QUECTEL_USB_CTL}" ]; then
    _pb "DDS query Quectel cell shield for SIM ID on $QUECTEL_USB_CTL"
    rm "$LI_FILE_ICCID" > /dev/null 2>&1
    echo -ne "AT+QCCID\r" > "$QUECTEL_USB_CTL" && \
    sleep 0.1 && timeout 1 cat -v < "$QUECTEL_USB_CTL" | grep QCCID > "$LI_FILE_ICCID"
    # when file is empty, try again
    if [ ! -s "$LI_FILE_ICCID" ]; then
        _pb "re-try, DDS query Quectel cell shield for SIM ID on $QUECTEL_USB_CTL"
        echo -ne "AT+QCCID\r" > "$QUECTEL_USB_CTL" && \
        sleep 0.1 && timeout 1 cat -v < "$QUECTEL_USB_CTL" | grep QCCID > "$LI_FILE_ICCID"
    fi
fi



echo && echo
_pb "-------------"
_pb "run DDS core "
_pb "-------------"
echo
cd "$FOL_DDH" && "$FOL_VEN"/bin/python main_dds.py
