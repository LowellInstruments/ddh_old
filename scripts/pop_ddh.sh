#!/usr/bin/bash


source colors.sh
echo; echo; echo


# constants
FTS=/tmp/ddh_stash
FA=/home/pi/li/ddh


_S="[ POP ] ddh | stashing configuration files"
_pb "$_S"
rm -rf $FTS
mkdir $FTS && \
cp $FA/settings/config.toml $FTS && \
cp $FA/scripts/script_logger_do_deploy_cfg.json $FTS && \
cp $FA/ddh/db/db_his.json $FTS
_e $? "$_S"



_S="[ POP ] ddh | getting last github DDH code"
_pb "$_S"
cd $FA && \
git reset --hard && \
git pull
_e $? "$_S"



_S="[ POP ] ddh | pip installing extra requirements"
_pb "$_S"
pip install -r $FA/requirements_rpi_39_2023_extra.txt
_e $? "$_S"




_S="[ POP ] ddh | un-stashing configuration files"
_pb "$_S"
cp $FTS/config.toml $FA/settings && \
cp $FTS/script_logger_do_deploy_cfg.json $FA/scripts && \
cp $FTS/db_his.json $FA/ddh/db
_e $? "$_S"



_S="[ POP ] ddh | installing Moana plugin from ddt folder"
_pb "$_S"
cd /home/pi/li/ddt && \
git reset --hard && \
git pull && \
cp /home/pi/li/ddt/_dt_files/ble_dl_moana.py $FA/dds
_e $? "$_S"


_pg "[ POP ] ddh | ran OK!"
