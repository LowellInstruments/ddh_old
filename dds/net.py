from dds.timecache import is_it_time_to
from utils.ddh_shared import send_ddh_udp_gui as _u
from utils.ddh_shared import STATE_DDS_NOTIFY_NET_VIA
import subprocess as sp
from utils.logs import lg_net as lg


_g_last_via = ""
IP = "8.8.8.8"


def _get_internet_via():

    # check we have any type of internet
    c = "timeout 2 ping -c 1 {}".format(IP)
    rv = sp.run(c, shell=True, stdout=sp.PIPE, stderr=sp.PIPE)
    if rv.returncode != 0:
        return "none"

    # we have internet, find out which type
    c = "ip route get {}".format(IP)
    rv = sp.run(c, shell=True, stdout=sp.PIPE, stderr=sp.PIPE)
    if b"ppp0" in rv.stdout:
        return "cell"
    if b"usb0" in rv.stdout:
        return "cell"
    return "wifi"


def ddh_get_internet_via():
    return _get_internet_via()


def net_serve():

    if not is_it_time_to("get_internet_via", 60):
        return

    via = _get_internet_via()
    _u(f"{STATE_DDS_NOTIFY_NET_VIA}/{via}")

    global _g_last_via
    if via != _g_last_via:
        if via == "none":
            lg.a("error: NET module found no internet access")
        else:
            lg.a(f"internet via {via}")
    _g_last_via = via


# test
if __name__ == "__main__":
    net_serve()
