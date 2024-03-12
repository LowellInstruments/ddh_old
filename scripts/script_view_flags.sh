#!/usr/bin/env bash


source utils.sh


CF=/etc/crontab


echo; echo;
echo 'this DDH:'
echo '---------'
echo



# create a file used to decide installing j4halt or not, among others
if [ -f "$EMOLT_FILE_FLAG" ]; then echo -e '\t emolt flag \t = 1'
else echo -e '\t emolt flag \t = 0'; fi



# create a file used on AWS uplink
if [ -f "$GROUPED_S3_FILE_FLAG" ]; then echo -e '\t AWS group \t = 1'
else echo -e '\t AWS group \t = 0'; fi



# create a file used on GPS detection
if [ -f "$GPS_EXTERNAL_FILE_FLAG" ]; then echo -e '\t GPS external \t = 1'
else echo -e '\t GPS external \t = 0 -> internal'; fi



# create a file to enter GRAPH test mode
if [ -f "$FILE_GRAPH_TEST_MODE" ]; then echo -e '\t graph test \t = 1'
else echo -e '\t graph test \t = 0'; fi



# create a file to enter GPS dummy mode
if [ -f "$GPS_DUMMY_MODE_FILE" ]; then echo -e '\t GPS dummy \t = 1'
else echo -e '\t GPS dummy \t = 0'; fi



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
