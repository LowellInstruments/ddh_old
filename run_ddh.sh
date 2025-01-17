#!/usr/bin/env bash
source /home/pi/li/ddh/scripts/utils.sh


echo


# check we need a reboot
if [ -f "$LI_DDH_NEEDS_REBOOT_POST_INSTALL" ]; then
    _pr "DDH was just installed, please reboot"
    exit 0
fi



# tweaking python files for PyQtWeb*Widgets
DESIGNER_MAIN_PY=$FOL_DDH/ddh/gui/designer_main.py
echo 'tweaking designer_main.py depending on laptop vs. raspberry'
sed -i 's/from PyQt5 import QtWebEngineWidgets/from PyQt5 import QtWebKitWidgets/g' "$DESIGNER_MAIN_PY"
sed -i 's/self.webView = QtWebEngineWidgets.QWebEngineView(self.tab_trawls)/self.webView = QtWebKitWidgets.QWebView(self.tab_trawls)/g' "$DESIGNER_MAIN_PY"



# for crontab to detect already running
check_already_running "main_ddh_controller"



_pb "DDH set XAUTHORITY, DISPLAY linux environment variables"
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
