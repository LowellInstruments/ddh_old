#!/usr/bin/env bash


source utils.sh


echo '----------------------------------------------------------------------------------'
echo 'DDH SCRIPT -> in progress'
source "$FOL_VEN"/bin/activate && \
cd "$FOL_DDH"/scripts && \
"$FOL_VEN"/bin/python ./script_logger_do_deploy.py
echo '----------------------------------------------------------------------------------'
