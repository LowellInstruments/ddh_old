#!/usr/bin/env bash


# script called by DDU-text utility, not used by DDU-gui
DDT_CF_RUN_API=/home/pi/li/ddt/_dt_files/crontab_api.sh
CF=/etc/crontab


echo; echo;
# -q: quiet output
grep -q crontab_api.sh $CF
rv=$?
if [ $rv -eq 1 ]; then
    # no string found in whole crontab, add it
    echo -e "* * * * * pi $DDT_CF_RUN_API\n" | sudo tee -a $CF
    echo "added API to empty crontab"
    exit 0
fi

# detect the commented line
grep crontab_api.sh $CF | grep -F '#' > /dev/null
rv=$?

# delete any lines containing "crontab_api.sh"
sudo sed -i '/crontab_api/d' $CF

if [ $rv -eq 0 ]; then
    echo "crontab API was OFF, trying toggle"
    echo "* * * * * pi $DDT_CF_RUN_API" | sudo tee -a $CF
    echo "crontab API ON"
else
    echo "crontab API was ON, disabling it..."
    echo "#* * * * * pi $DDT_CF_RUN_API" | sudo tee -a $CF
    echo "crontab API OFF"
fi

sudo systemctl restart cron.service
echo "crontab service restarted"
