#!/usr/bin/bash
echo; echo; echo


F_VE=/home/pi/li/venv
PIP=$F_VE/bin/pip3
F_CLONE_LIU=/tmp/liu


echo "pop_liu -> activating VENV"
source $F_VE/bin/activate
rv=$?; if [ $rv -ne 0 ]; then echo 'error: LIU activate VENV'; exit 1; fi



echo "pop_liu -> uninstalling previous, if any"
$PIP uninstall -y liu


echo "pop_liu -> cloning newest from github"
rm -rf $F_CLONE_LIU
git clone https://github.com/lowellinstruments/liu.git $F_CLONE_LIU
rv=$?; if [ $rv -ne 0 ]; then echo 'error: cloning LIU'; exit 1; fi


echo "pop_liu -> installing"
$PIP install $F_CLONE_LIU
rv=$?; if [ $rv -ne 0 ]; then echo 'error: PIP installing'; exit 1; fi


echo "pop_liu -> create commit file"
COM_LIU_LOC=$(cd "$F_CLONE_LIU" && git rev-parse master); rv=$?;
if [ "$rv" -ne 0 ]; then echo "error: cannot get LIU local version"; fi
if [ ${#COM_LIU_LOC} -ne 40 ]; then echo "error: bad LIU local version"; fi
sudo echo "$COM_LIU_LOC" | sudo tee /etc/com_liu_loc.txt > /dev/null
rv=$?; if [ $rv -ne 0 ]; then echo 'error: creating LIU commit file'; exit 1; fi
