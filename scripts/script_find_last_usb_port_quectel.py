#!/usr/bin/env python

import time
import serial.tools.list_ports
import subprocess as sp

for p in serial.tools.list_ports.comports():
    # ordered big to small
    if p.manufacturer == 'Quectel':
        print(f'found last quectel USB port on {p.name}')
        # dont touch this
        c = f'echo -ne "AT+QCCID\\r" > /dev/{p.name}'
        sp.run(c, shell=True, stderr=sp.PIPE, stdout=sp.PIPE)
        time.sleep(.1)
        c = 'cat -v < /dev/{p.name} | grep QCCID > /home/pi/li/.iccid'
        rv = sp.run(c, shell=True, stderr=sp.PIPE, stdout=sp.PIPE)
        break

