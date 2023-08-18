BLE dongles summary
-------------------

Run the following command to know the Linux release year of your DDH. 
We show a possible answer.

```console
$ cat /boot/issue.txt
Raspberry Pi reference 2023-05-03
```

To see the version of your dongle, connect it and run the following command. 
We show a possible answer. You can see the Bluetooth version on line `HCI version`.

```console
$ hciconfig -a
hci1:   Type: Primary  Bus: USB
            BD Address: E8:4E:06:96:F4:39  ACL MTU: 1021:8  SCO MTU: 255:12
            UP RUNNING
            RX bytes:6281 acl:0 sco:0 events:365 errors:0
            TX bytes:36597 acl:0 sco:0 commands:252 errors:0
            Features: 0xff 0xff 0xff 0xfe 0xdb 0xfd 0x7b 0x87
            Packet type: DM1 DM3 DM5 DH1 DH3 DH5 HV1 HV2 HV3
            Link policy: RSWITCH HOLD SNIFF PARK
            Link mode: SLAVE ACCEPT
            Name: 'raspberrypi #2'
            Class: 0x2c0000
            Service Classes: Rendering, Capturing, Audio
            Device Class: Miscellaneous,
            HCI Version: 4.2 (0x8)  Revision: 0x829a
            LMP Version: 4.2 (0x8)  Subversion: 0x7644
            Manufacturer: Realtek Semiconductor Corporation (93)
```

If your year is 2022, your DDH will accept BLE external dongles v4.2.
If your year is 2023, your DDH will accept BLE external dongles v4.2 and 5.x.
