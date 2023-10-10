#!/usr/bin/bash
echo; echo; echo


F_VE=/home/pi/li/venv
PIP=$F_VE/bin/pip3
F_CLONE_MAT=/tmp/mat


echo "pop_mat -> activating VENV"
source $F_VE/bin/activate
rv=$?; if [ $rv -ne 0 ]; then echo 'error: MAT activate VENV'; exit 1; fi



echo "pop_mat -> uninstalling previous, if any"
$PIP uninstall -y mat


echo "pop_mat -> cloning newest from github"
rm -rf $F_CLONE_MAT
git clone https://github.com/lowellinstruments/mat.git $F_CLONE_MAT
rv=$?; if [ $rv -ne 0 ]; then echo 'error: cloning MAT'; exit 1; fi


echo "pop_mat -> installing"
$PIP install $F_CLONE_MAT
rv=$?; if [ $rv -ne 0 ]; then echo 'error: PIP installing'; exit 1; fi


echo "pop_mat -> create commit file"
COM_MAT_LOC=$(cd "$F_CLONE_MAT" && git rev-parse master); rv=$?;
if [ "$rv" -ne 0 ]; then echo "error: cannot get MAT local version"; fi
if [ ${#COM_MAT_LOC} -ne 40 ]; then echo "error: bad MAT local version"; fi
sudo echo "$COM_MAT_LOC" | sudo tee /etc/com_mat_loc.txt > /dev/null
rv=$?; if [ $rv -ne 0 ]; then echo 'error: creating MAT commit file'; exit 1; fi


echo "pop_mat -> done!"

