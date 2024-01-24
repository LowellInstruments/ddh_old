#!/usr/bin/env bash

echo; echo;
echo '----------------------------------------------------------------------------------'
printf 'DDH kill \n'
echo '----------------------------------------------------------------------------------'
pkill -F /tmp/main_dds_controller.pid 2> /dev/null
pkill -F /tmp/main_ddh_controller.pid 2> /dev/null
pkill -F /tmp/main_dds.pid 2> /dev/null
pkill -F /tmp/main_ddh.pid 2> /dev/null

echo 'done DDH kill'
