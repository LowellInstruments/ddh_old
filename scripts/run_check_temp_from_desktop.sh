#!/usr/bin/env bash

echo; echo;
printf '\nR> RPI temperature test \n'
source /home/pi/li/venv/bin/activate
cd /home/pi/li/ddh/scripts && python ./check_rpi_temperature.py
read -r
