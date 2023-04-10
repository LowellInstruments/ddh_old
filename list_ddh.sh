#!/usr/bin/bash
echo; echo; echo


echo '> listing DDH and DDS processes'; echo
ps -aux | grep main_ddh | grep -v grep
ps -aux | grep main_dds | grep -v grep
echo; echo; echo
