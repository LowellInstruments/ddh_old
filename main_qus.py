#!/usr/bin/env python3


# ------------------------------------
# main Quectel USB: detects which USB
# ports are being used by cell shield
# ------------------------------------


import serial
import time


SERIAL_RATE = 115200


def detect_quectel_usb_ports():
    found_gps = ''
    found_ctrl = ''
    for i in range(5):
        p = f'/dev/ttyUSB{i}'
        till = time.perf_counter() + 1
        b = bytes()
        ser = None
        try:
            ser = serial.Serial(p, SERIAL_RATE, timeout=.1, rtscts=True, dsrdtr=True)
            ser.write(b'AT+CVERSION \rAT+CVERSION \r')
            while time.perf_counter() < till:
                b += ser.read()
                if b'$GPGSV' in b or b'$GPGSA' in b or b'GPRMC' in b:
                    found_gps = p
                    break
                if b'VERSION' in b:
                    found_ctrl = p
                    break
            ser.close()
            if found_gps and found_ctrl:
                break
        except (Exception,) as ex:
            if ser and ser.isOpen():
                ser.close()
            # print(f'error {p} -> {ex}')
    with open('/tmp/usb_quectel_gps', 'w') as f:
        f.write(found_gps)
    with open('/tmp/usb_quectel_ctrl', 'w') as f:
        f.write(found_ctrl)
    return found_gps, found_ctrl


if __name__ == '__main__':
    rv = detect_quectel_usb_ports()
    print('rv', rv)


