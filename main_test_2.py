from dds.ble_dl_tdo_lsb import ble_interact_tdo_lsb
from datetime import datetime

from lsb.connect import force_disconnect


def main_test_lsb(_m):
        u = '222222222'
        _i = "TDO"
        _g = ("+1.111111", "-2.222222", datetime.now(), 0)
        _h = "hci0"
        _args = [_m, _i, _g, _h, u]
        ble_interact_tdo_lsb(*_args)


# test
if __name__ == '__main__':
    mac = "F0:5E:CD:25:9D:D2"
    force_disconnect(mac)
    main_test_lsb(mac)
