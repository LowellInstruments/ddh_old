#!/usr/bin/env bash


source utils.sh


echo; echo;
echo '----------------------------------------------------------------------------------'
printf 'DDH buttons test \n'
echo '----------------------------------------------------------------------------------'
source "$FOL_VEN"/bin/activate && \
cd "$FOL_DDH"/scripts && \
python ./check_buttons.py
read -r
