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

Release year 2022 accepts BLE dongles v4.2. Release year 2023 accepts BLE external dongles v4.2 and 5.x.

## License

This project is licensed under GPL License - see COPYING file for details
