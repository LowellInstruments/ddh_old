#!/usr/bin/env bash

echo; echo;
echo '----------------------------------------------------------------------------------'
printf 'DDH buttons test \n'
echo '----------------------------------------------------------------------------------'
source /home/pi/li/venv/bin/activate
cd /home/pi/li/ddh/scripts && python ./check_buttons.py
read -r
