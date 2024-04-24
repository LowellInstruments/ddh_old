#!/usr/bin/env bash


# consider we are inside 'ddh' being called from 'main_ddc'
source scripts/utils.sh


# we change the directory here to 'scripts'
echo
echo '-------------------------------------------'
echo 'logger DOX deploy'
source "$FOL_VEN"/bin/activate && \
cd "$FOL_DDH"/scripts && \
"$FOL_VEN"/bin/python "$FOL_DDH"/scripts/script_logger_dox_deploy.py
echo '-------------------------------------------'
