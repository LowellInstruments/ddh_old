#!/usr/bin/bash



source colors.sh
echo; echo; echo



F_VE=/home/pi/li/venv
PIP=$F_VE/bin/pip3
F_CLONE_MAT=/tmp/mat



_S="[ POP ] mat | activating VENV"
_pb "$_S"
source $F_VE/bin/activate
_e $? "$_S"



_S="[ POP ] mat | uninstalling previous library, if any"
_pb "$_S"
$PIP uninstall -y mat
_e $? "$_S"



_S="[ POP ] mat | cloning newest code from github to /tmp"
_pb "$_S"
rm -rf $F_CLONE_MAT
git clone https://github.com/lowellinstruments/mat.git $F_CLONE_MAT
_e $? "$_S"



_S="[ POP ] mat | installing it via pip"
_pb "$_S"
$PIP install $F_CLONE_MAT
_e $? "$_S"



_S="[ POP ] mat | creating commit local file"
_pb "$_S"
COM_MAT_LOC=$(cd "$F_CLONE_MAT" && git rev-parse master)
_e $? "cannot get MAT local commit file"
[ ${#COM_MAT_LOC} -ne 40 ]
_e $? "bad MAT local commit file"
sudo echo "$COM_MAT_LOC" | sudo tee /etc/com_mat_loc.txt > /dev/null
_e $? "cannot copy MAT commit file to /etc/"



_pb "[ POP ] mat | ran OK!"

