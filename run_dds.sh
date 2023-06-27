#!/usr/bin/env bash
F_VE=/home/pi/li/venv
F_DA=/home/pi/li/ddh


# for crontab: to detect already running
ps -aux | grep "main_dds_controller" | grep -v grep
ALREADY=$?
if [ "$ALREADY" -eq 0 ]; then echo "DDS already running in bash, leaving"; exit 0; fi


# AWS credentials

export DDH_AWS_BUCKET=
export DDH_AWS_KEY_ID=
export DDH_AWS_SECRET=
export DDH_BOX_SERIAL_NUMBER=
export DDH_BOX_PROJECT_NAME=
export DDH_SQS_QUEUE_NAME=ddw_in.fifo


echo; echo 'R > bluetooth power check'
sudo hciconfig hci0 up || true
sudo hciconfig hci1 up || true


echo; echo 'R > bluetooth sanity check'
hciconfig hci0 | grep RUNNING > /dev/null; rv_hci0=$?
hciconfig hci1 | grep RUNNING > /dev/null; rv_hci1=$?
if [ $rv_hci0 -ne 0 ] && [ $rv_hci1 -ne 0 ]; then
    printf "error: all Bluetooth hci seem bad\n"
    exit 1
fi


echo; echo 'R > ensure rfkill wlan unblock'
sudo rfkill unblock wlan


echo; echo 'R > permissions date / ifmetric'
sudo setcap CAP_SYS_TIME+ep /bin/date
sudo setcap 'cap_net_raw,cap_net_admin+eip' /usr/sbin/ifmetric


echo; echo 'R > calling DDS main python code'
sudo chown -R pi:pi "$F_DA"
source "$F_VE"/bin/activate
cd "$F_DA" && $F_VE/bin/python main_dds.py
