#!/usr/bin/env bash


source ./utils.sh



echo '----------------------------------------------------------------------------------'
echo 'DDH logger DO deploy, script in progress'
source "$FOL_VEN"/bin/activate && \
cd "$FOL_DDH"/scripts && \
"$FOL_VEN"/bin/python "$FOL_DDH"/scripts/script_logger_do_deploy.py
echo '----------------------------------------------------------------------------------'
