#!/usr/bin/env bash
source /home/pi/li/ddh/scripts/utils.sh


clear
echo



_pb "disabling service NET from Lowell Instruments"
sudo systemctl stop unit_switch_net.service


_pb "setting cell as default output network interface"
sudo setcap 'cap_net_raw,cap_net_admin+eip' /usr/sbin/ifmetric
sudo /usr/sbin/ifmetric wlan0 400
sudo /usr/sbin/ifmetric ppp0 0



_pb "test ngrok is installed"
ngrok
rv=$?
if [ $rv -ne 0 ]; then
    MY_ARCH=$(arch)
    MY_OUT=/home/pi/li/Downloads/ngrok.tgz
    _pb "ngrok not installed, installing ngrok $MY_ARCH"
    if [ "$MY_ARCH" == "aarch64" ]; then
        wget -O $MY_OUT https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-arm64.tgz
    elif [ "$MY_ARCH" == "arm7vl" ]; then
        wget -O $MY_OUT https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-arm.tgz
    fi
    sudo tar -xvzf $MY_OUT -C /usr/local/bin
fi


_pb "open ngrok tunnel to port 22"
# ngrok runs remotely, we don't need sudo
ngrok config add-authtoken 2lslTteWfMioUxAggtQvgY0yM42_7LJhKttjudg3k28feRmJX
ngrok tcp 22


# ASK the user to tell us the tunnel name such as 8.tcp.ngrok.io:15290
# support will do:
#     $ ssh pi@8.tcp.ngrok.io -p 15290
