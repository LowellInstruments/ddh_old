#!/usr/bin/bash
echo; echo; echo


# colors red, blue and reset
C_R="\033[0;31m"
C_B="\033[0;34m"
C_Z="\033[0m"


# constants
FTS=/tmp/ddh_stash
FA=/home/pi/li/ddh



echo -e "${C_B}>>> stashing current DDS configuration\n${C_Z}"
rm -rf $FTS
mkdir $FTS
cp $FA/run_dds.sh $FTS
cp $FA/scripts/script_logger_do_deploy_cfg.json $FTS
cp $FA/settings/_li_all_macs_to_sn.yml $FTS
cp $FA/settings/ctx.py $FTS
cp $FA/settings/ddh.json $FTS
cp $FA/ddh/db/db_his.db $FTS



echo -e "${C_B}>>> resetting and pulling DDH from github\n${C_Z}"
cd $FA || (echo -e "${C_R}error: no DDH app folder${C_Z}"; exit 1)
git reset --hard
git pull
rv=$?
if [ $rv -ne 0 ]; then
    echo -en "${C_R}"
    echo "error: cannot DDH git pull"
    echo "check your current configuration files"
    echo "recover from ${FTS} if they ended up wrong"
    echo -en "${C_Z}"
    exit 1
fi



echo -e "${C_B}>>> un-stashing DDS configuration\n${C_Z}"
cp $FTS/run_dds.sh $FA
cp $FTS/script_logger_do_deploy_cfg.json $FA/scripts
cp $FTS/_li_all_macs_to_sn.yml $FA/settings
cp $FTS/ctx.py $FA/settings
cp $FTS/ddh.json $FA/settings
cp /home/pi/li/ddt/_dt_files/ble_dl_moana.py $FA/dds
cp $FTS/db_his.db $FA/ddh/db



echo -e "${C_B}\n>>> done\n${C_Z}"
