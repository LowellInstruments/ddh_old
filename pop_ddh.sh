#!/usr/bin/bash
echo; echo; echo


FTS=/tmp/stash_ddh
FA=/home/pi/li/ddh


echo '>>> stashing current DDS configuration'
echo
rm -rf $FTS
mkdir $FTS
cp run_dds.sh $FTS
cp scripts/script_logger_do_deploy_cfg.json $FTS
cp settings/_li_all_macs_to_sn.yml $FTS
cp settings/ctx.py $FTS
cp settings/ddh.json $FTS


echo '>>> resetting and pulling DDH from github'
echo
git reset --hard
git pull
rv=$?
if [ $rv -ne 0 ]; then
    echo
    echo 'careful, script reset after git pull, may leave wrong ddh.json'
    exit 1
fi


echo '>>> restoring stashed DDS configuration'
echo
cp $FTS/run_dds.sh $FA
cp $FTS/script_logger_do_deploy_cfg.json $FA/scripts
cp $FTS/_li_all_macs_to_sn.yml $FA/settings
cp $FTS/ctx.py $FA/settings
cp $FTS/ddh.json $FA/settings
cp /home/pi/li/ddt/_dt_files/ble_dl_moana.py $FA/dds

echo; echo '>>> done'; echo
