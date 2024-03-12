#!/usr/bin/env bash


# CF: crontab file
DDT_CF_RUN_DDH=/home/pi/li/ddt/_dt_files/crontab_ddh.sh
CF=/etc/crontab


echo; echo;
# -q: quiet output
grep -q crontab_ddh.sh $CF
rv=$?
if [ $rv -eq 1 ]; then
    # no string found in whole crontab, add it
    echo -e "* * * * * pi $DDT_CF_RUN_DDH\n" | sudo tee -a $CF
    echo "added DDH to empty crontab"
    exit 0
fi

# detect the commented line
grep crontab_ddh.sh $CF | grep -F '#' > /dev/null
rv=$?

# delete any lines containing "crontab_ddh.sh"
sudo sed -i '/crontab_ddh/d' $CF

if [ $rv -eq 0 ]; then
    echo "crontab DDH was OFF, trying toggle"
    echo "* * * * * pi $DDT_CF_RUN_DDH" | sudo tee -a $CF
    echo "crontab DDH ON"
else
    echo "crontab DDH was ON, disabling it..."
    echo "#* * * * * pi $DDT_CF_RUN_DDH" | sudo tee -a $CF
    echo "crontab DDH OFF"
fi

sudo systemctl restart cron.service
echo "crontab service restarted"
