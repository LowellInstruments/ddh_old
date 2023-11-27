#!/usr/bin/env bash


# script called by DDU-text utility, not used by DDU-gui

EMOLT_FILE_FLAG=/home/pi/li/.ddt_this_is_emolt_box.flag
GROUPED_S3_FILE_FLAG=/home/pi/li/.ddt_this_box_has_grouped_s3_uplink.flag
CF=/etc/crontab
FILE_GRAPH_TEST_MODE=/tmp/ddh_graph_test_mode.json
FILE_GRAPH_ENABLER=/home/pi/li/.ddh_graph_enabler.json
GPS_DUMMY_MODE_FILE=/tmp/gps_dummy_mode.json


echo; echo;
echo 'this DDH:'
echo '---------'
echo

if [ -f "$EMOLT_FILE_FLAG" ]; then echo -e '\t emolt flag \t = 1'
else echo -e '\t emolt flag \t = 0'; fi

if [ -f "$GROUPED_S3_FILE_FLAG" ]; then echo -e '\t AWS group \t = 1'
else echo -e '\t AWS group \t = 0'; fi

grep -q crontab_ddh.sh $CF; rv=$?
if [ $rv -eq 1 ]; then echo -e '\t crontab DDH \t = 0'
else
  grep crontab_ddh.sh $CF | grep -F '#' > /dev/null; rv=$?
  if [ $rv -eq 0 ]; then echo -e "\t crontab DDH \t = 0"
  else echo -e "\t crontab DDH \t = 1"; fi
fi
grep -q crontab_api.sh $CF; rv=$?
if [ $rv -eq 1 ]; then echo -e '\t crontab API \t = 0'
else
  grep crontab_api.sh $CF | grep -F '#' > /dev/null; rv=$?
  if [ $rv -eq 0 ]; then echo -e "\t crontab API \t = 0"
  else echo -e "\t crontab API \t = 1"; fi
fi

if [ -f "$FILE_GRAPH_TEST_MODE" ]; then echo -e '\t graph test \t = 1'
else echo -e '\t graph test \t = 0'; fi

if [ -f "$FILE_GRAPH_ENABLER" ]; then echo -e '\t graph enabler \t = 1'
else echo -e '\t graph enabler \t = 0'; fi

if [ -f "$GPS_DUMMY_MODE_FILE" ]; then echo -e '\t GPS dummy \t = 1'
else echo -e '\t GPS dummy \t = 0'; fi
