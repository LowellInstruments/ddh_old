import json
import threading

import time

from dds.timecache import is_it_time_to
from utils.ddh_shared import send_ddh_udp_gui as _u
from utils.ddh_shared import STATE_DDS_NOTIFY_NET_VIA
import subprocess as sp
from utils.logs import lg_net as lg
from utils.flag_paths import TMP_PATH_INET_VIA

_g_last_via = ""
IP = "8.8.8.8"


def _get_internet_via():

    # check we have ANY type of internet
    c = f"timeout 1 ping -c 1 www.google.com -4"
    for i in range(3):
        rv = sp.run(c, shell=True, stdout=sp.PIPE, stderr=sp.PIPE)
        if rv.returncode == 0:
            # we are doing well
            break
        if i == 2:
            return "none"
        time.sleep(.1)

    # we have internet, find out which type
    c = f"ip route get {IP}"
    rv = sp.run(c, shell=True, stdout=sp.PIPE, stderr=sp.PIPE)
    if b"ppp0" in rv.stdout:
        return "cell"
    if b"usb0" in rv.stdout:
        return "cell"
    return "wifi"


def ddh_get_internet_via():
    return _get_internet_via()


def _th_net_serve():
    via = _get_internet_via()
    _u(f"{STATE_DDS_NOTIFY_NET_VIA}/{via}")
    global _g_last_via
    if via != _g_last_via:
        if via == "none":
            lg.a("error: NET module found no internet")
        else:
            lg.a(f"internet via {via}")
    _g_last_via = via

    # save to file for API purposes
    try:
        with open(TMP_PATH_INET_VIA, "w") as f:
            json.dump({"internet_via": via}, f)
    except (Exception, ) as ex:
        lg.a(f'error: saving {TMP_PATH_INET_VIA} -> {ex}')


def net_serve():
    if not is_it_time_to("get_internet_via", 300):
        return
    th = threading.Thread(target=_th_net_serve)
    th.start()


# test
if __name__ == "__main__":
    net_serve()
