#!/usr/bin/env bash


# script called by DDU-text utility, not used by DDU-gui
DDH_STR=/home/pi/li/ddt/_dt_files/crontab_ddh.sh
CF=/etc/crontab


echo; echo;
# -q: quiet output
grep -q crontab_ddh.sh $CF
rv=$?
if [ $rv -eq 1 ]; then
    # no "crontab_ddh/api.sh" string found in whole crontab, add it
    echo -e "* * * * * pi $DDH_STR\n" | sudo tee -a $CF
    echo "added DDH to empty crontab"
fi

# detect the commented line
grep crontab_ddh.sh $CF | grep '#' > /dev/null
rv=$?

# delete any lines containing "crontab_ddh.sh"
sudo sed -i '/crontab_ddh/d' $CF

if [ $rv -eq 0 ]; then
    echo "crontab DDH was OFF, trying toggle"
    echo "* * * * * pi $DDH_STR" | sudo tee -a $CF
    echo "crontab DDH ON"
else
    echo "crontab DDH was ON, disabling it..."
    echo "#* * * * * pi $DDH_STR" | sudo tee -a $CF
    echo "crontab DDH OFF"
fi

sudo systemctl restart cron.service
echo "crontab service restarted"
