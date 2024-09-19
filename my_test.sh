ALL_MY_HCI_MACS=$(hciconfig -a | grep "BD Address" | cut -d " " -f 3)
for each_hci_mac in $ALL_MY_HCI_MACS
do
    rm "/var/lib/bluetooth/$each_hci_mac"/cache/*
done
