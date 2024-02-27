# Deck Data Hub

Application to download Bluetooth-enabled data loggers in fishing and research vessels.

![alt text](ddh/gui/res/screenshot.png)

## BLE dongles

DDH can work with internal or external Bluetooth. Get your DDH Linux release year with: 

```console
$ cat /boot/issue.txt
Raspberry Pi reference 2023-05-03
```

To see the Bluetooth version of your USB dongle, connect it to the DDH and run: 

```console
$ hciconfig -a
hci1:   Type: Primary  Bus: USB
            BD Address: E8:4E:06:__:__:__  ACL MTU: 1021:8  SCO MTU: 255:12
            UP RUNNING
            ...
            HCI Version: 4.2 (0x8)  Revision: 0x829a
            LMP Version: 4.2 (0x8)  Subversion: 0x7644
            Manufacturer: Realtek Semiconductor Corporation (93)
```

Release year 2022 accepts BLE dongles v4.2. Release year 2023 seems to also accept BLE external 5.x.

5.x EDUP dongles have VID/PID 2550:8761 Realtek Bluetooth Radio
4.x EDUP dongles have VID/PID 0bda:c820 Realtek Semiconductor Corp. 802.11ac NIC
4.x LM   dongles have VID/PID 0a5c:21e8 Broadcom Corp. BCM20702A0 Bluetooth 4.0

## GUI shortcuts

To enable / disable Bluetooth, press 'b' key, release it and click main icon text.
To show / hide edit tab, press 'e' key, release it and click main icon text.
To show / hide edit tab, you can also hold the boat icon for 5 seconds.
To minimize GUI, press 'm' key, release it and click main icon text.
To minimize GUI, you can also hold the GUI field containing the datetime for 5 seconds.
To show / hide recipe tab, you can hold the GUI field containing the version for 5 seconds. 
To force a cloud sync, you can click the cloud icon.
To quit DDH, press 'q' key, release it and click main icon text.

## License

This project is licensed under GPL License - see COPYING file for details
