#!/usr/bin/env python

import time
import serial.tools.list_ports
import subprocess as sp

ls = []
for p in serial.tools.list_ports.comports():
    # ordered big to small
    if '2C7C:0125' in p.hwid:
        ls.append(p.name)

if ls:
    v = ls[-2]
    c = f'echo -ne "AT+QCCID\r" > /dev/{v}'
    print(c)
    sp.run(c, shell=True, stderr=sp.PIPE, stdout=sp.PIPE)
    time.sleep(.1)
    c = f'timeout 1 cat -v < /dev/{v} | grep QCCID > /home/pi/li/.iccid'
    rv = sp.run(c, shell=True, stderr=sp.PIPE, stdout=sp.PIPE)
