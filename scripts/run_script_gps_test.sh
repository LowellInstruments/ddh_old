#!/usr/bin/env bash


source utils.sh


echo; echo;
echo '----------------------------------------------------------------------------------'
printf '\nR> GPS quectel test \n'
echo '----------------------------------------------------------------------------------'
source "$FOL_VEN"/bin/activate && \
cd "$FOL_DDH"/scripts && \
python ./check_gps_quectel.py
read -r
