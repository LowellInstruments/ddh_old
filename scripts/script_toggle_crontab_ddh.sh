#!/usr/bin/env bash


# script called by DDU-text utility, not used by DDU-gui
DDH_STR=/home/pi/li/ddt/_dt_files/crontab_ddh.sh
CF=/etc/crontab


echo; echo;
grep crontab_ddh.sh $CF
rv=$?
if [ $rv -eq 1 ]; then
    # no "crontab_ddh/api.sh" string found in whole crontab, add it
    echo -e "* * * * * pi $DDH_STR\n" | sudo tee -a $CF
    echo "added DDH to empty crontab"
fi
grep crontab_ddh.sh $CF | grep '#'
if [ $rv -eq 0 ]; then
    # crontab_ddh is there disabled, we want to activate == uncomment it
    sudo sed -i '/crontab_ddh.sh/s/^#//g' $CF
    echo "crontab DDH enabled"
else
    # crontab_ddh is there enabled, we want to disable == comment it
    sudo sed -i '/crontab_ddh.sh/s/^/#/g' $CF
    echo "crontab DDH OFF"
fi
