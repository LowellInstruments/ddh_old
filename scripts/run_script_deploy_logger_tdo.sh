#!/usr/bin/env bash


source ./utils.sh



echo '----------------------------------------------------------------------------------'
echo 'DDH logger TDO deploy, script in progress'
source "$FOL_VEN"/bin/activate && \
cd "$FOL_DDH"/scripts && \
"$FOL_VEN"/bin/python "$FOL_DDH"/scripts/script_logger_tdo_deploy.py
echo '----------------------------------------------------------------------------------'
