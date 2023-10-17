#!/usr/bin/env bash


# script called by DDU-text utility, not used by DDU-gui

EMOLT_FILE_FLAG=/home/pi/li/.ddt_this_is_emolt_box.flag
GROUPED_S3_FILE_FLAG=/home/pi/li/.ddt_this_box_has_grouped_s3_uplink.flag
CF=/etc/crontab
FILE_GRAPH_TEST_MODE=/tmp/ddh_graph_test_mode.json
FILE_GRAPH_ENABLER=/home/pi/.ddh_graph_enabler.json
GPS_DUMMY_MODE_FILE=/tmp/gps_dummy_mode.json


echo; echo;
echo 'this box has:'
if [ -f "$EMOLT_FILE_FLAG" ]; then echo -e '\t emolt flag'
else echo -e '\t pure DDH flag'; fi

if [ -f "$GROUPED_S3_FILE_FLAG" ]; then echo -e '\t AWS group sync'
else echo -e '\t AWS MAC sync'; fi

grep -q crontab_ddh.sh $CF; rv=$?
if [ $rv -eq 1 ]; then echo -e '\t no DDH on crontab'
else
  grep crontab_ddh.sh $CF | grep -F '#' > /dev/null; rv=$?
  if [ $rv -eq 0 ]; then echo -e "\t DDH OFF in crontab"
  else echo -e "\t DDH ON in crontab"; fi
fi
grep -q crontab_api.sh $CF; rv=$?
if [ $rv -eq 1 ]; then echo -e '\t no API on crontab'
else
  grep crontab_api.sh $CF | grep -F '#' > /dev/null; rv=$?
  if [ $rv -eq 0 ]; then echo -e "\t API OFF in crontab"
  else echo -e "\t API ON in crontab"; fi
fi

if [ -f "$FILE_GRAPH_TEST_MODE" ]; then echo -e '\t graph test ON'
else echo -e '\t graph test OFF'; fi

if [ -f "$FILE_GRAPH_ENABLER" ]; then echo -e '\t graph enabler ON'
else echo -e '\t graph enabler OFF'; fi

if [ -f "$GPS_DUMMY_MODE_FILE" ]; then echo -e '\t GPS dummy ON'
else echo -e '\t GPS dummy OFF'; fi
