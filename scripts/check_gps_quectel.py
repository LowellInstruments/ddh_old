import serial
import sys

sys.path.append("..")
from dds.gps import (  # noqa: E402
    gps_configure_shield,
    _gps_parse_rmc_frame,
    _gps_parse_gsv_frame,
)

# hardcoded, since they are FIXED on SixFab hats
PORT_DATA = "/dev/ttyUSB1"


def _coord_decode(coord: str):
    # src: stackoverflow 18442158 latitude format
    x = coord.split(".")
    head = x[0]
    deg = head[:-2]
    minutes = "{}.{}".format(head[-2:], x[1])
    decimal = int(deg) + float(minutes) / 60
    return decimal


def _gps_measure():
    sp = serial.Serial(
        PORT_DATA, baudrate=115200, timeout=0.1, rtscts=True, dsrdtr=True
    )
    sp.flushInput()
    while 1:
        b = sp.readall()
        if not b:
            continue
        _gps_parse_gsv_frame(b, force_print=True)
        g = _gps_parse_rmc_frame(b)
        print(g)


def main():
    try:
        gps_configure_shield()
        while 1:
            _gps_measure()
    except (Exception, ) as ex:
        print(f'error gps_test -> {ex}')
        print(f'ensure GPS was ON for a while before trying')


if __name__ == "__main__":
    main()
