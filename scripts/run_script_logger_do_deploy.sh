#!/usr/bin/env bash



FOL_VEN=/home/pi/li/ven

echo '----------------------------------------------------------------------------------'
echo 'DDH SCRIPT -> in progress'
source "$FOL_VEN"/bin/activate && \
cd "$FOL_DDH"/scripts && \
"$FOL_VEN"/bin/python ./script_logger_do_deploy.py
echo '----------------------------------------------------------------------------------'
