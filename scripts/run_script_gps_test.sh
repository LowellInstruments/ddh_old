#!/usr/bin/env bash

echo; echo;
echo '----------------------------------------------------------------------------------'
printf '\nR> GPS quectel test \n'
echo '----------------------------------------------------------------------------------'
source /home/pi/li/venv/bin/activate
cd /home/pi/li/ddh/scripts && python ./check_gps_quectel.py
read -r
