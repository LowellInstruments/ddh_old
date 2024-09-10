#!/usr/bin/env bash
source /home/pi/li/ddh/scripts/utils.sh


clear
echo



_pb "disabling service NET from Lowell Instruments"
sudo systemctl stop unit_switch_net.service


_pb "setting cell as default output network interface"
sudo setcap 'cap_net_raw,cap_net_admin+eip' /usr/sbin/ifmetric
sudo ifmetric wlan0 400
sudo ifmetric ppp0 0


# _pb "install ngrok"
# wget https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-arm64.tgz -P ~/Downloads
# sudo tar -xvzf ~/Downloads/ngrok-v3-stable-linux-arm64.tgz -C /usr/local/bin



_pb "open ngrok tunnel to port 22"
# ngrok runs remotely, we don't need sudo
ngrok config add-authtoken 2lslTteWfMioUxAggtQvgY0yM42_7LJhKttjudg3k28feRmJX
ngrok tcp 22


# ASK the user to tell us the tunnel name such as 8.tcp.ngrok.io:15290
# support will do:
#     $ ssh pi@8.tcp.ngrok.io -p 15290
