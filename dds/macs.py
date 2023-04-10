import glob
import os
import pathlib
import time
from utils.ddh_shared import (
    get_dds_folder_path_macs,
    get_ddh_loggers_forget_time,
    get_ddh_folder_path_macs_black,
    get_ddh_folder_path_macs_orange,
)
from utils.logs import lg_dds as lg


# -------------------------------------------------------
# small and file-based database of black and orange macs
# -------------------------------------------------------


PERIOD_MACS_ORANGE_SECS = 15


def dds_macs_color_show_at_boot():
    b = macs_black()
    o = macs_orange()
    lg.a("boot macs_black  = {}".format(b))
    lg.a("boot macs_orange = {}".format(o))


def dds_create_folder_macs_color():
    r = get_dds_folder_path_macs()
    os.makedirs(r, exist_ok=True)
    r = get_ddh_folder_path_macs_black()
    os.makedirs(r, exist_ok=True)
    r = get_ddh_folder_path_macs_orange()
    os.makedirs(r, exist_ok=True)


def _macs_get_them_by_color(s) -> list:
    assert s in ("orange", "black")
    valid = []
    now = int(time.time())
    fol = str(get_dds_folder_path_macs() / s)
    wc = "{}/*".format(fol)

    for f in glob.glob(wc):
        mac, t = f.split("@")
        if now > int(t):
            lg.a("MACS purge {}".format(f))
            os.unlink(f)
        else:
            valid.append(mac)
    return valid


def macs_black():
    return _macs_get_them_by_color("black")


def macs_orange():
    return _macs_get_them_by_color("orange")


def _add_mac(c, mac):
    assert c in ("orange", "black")
    ft = get_ddh_loggers_forget_time()
    if c == "orange":
        ft = PERIOD_MACS_ORANGE_SECS
    t = int(time.time()) + ft
    fol = str(get_dds_folder_path_macs() / c)
    mac = mac.replace(":", "-")
    f = "{}/{}@{}".format(fol, mac, t)
    pathlib.Path(f).touch()
    s = "{}'ed mac {}, value {}, now {}"
    now = int(time.time())
    lg.a(s.format(c, mac, t, now))


def _rm_mac(c, m):
    assert c in ("orange", "black")
    m = m.replace(":", "-")
    fol = str(get_dds_folder_path_macs() / c)
    wc = "{}/{}@*".format(fol, m)
    for f in glob.glob(wc):
        lg.a("MACS delete {}".format(f))
        os.unlink(f)


def add_mac_black(m):
    _add_mac("black", m)


def add_mac_orange(m):
    _add_mac("orange", m)


def rm_mac_black(m):
    _rm_mac("black", m)


def rm_mac_orange(m):
    _rm_mac("orange", m)


def is_mac_in_black(m):
    b = macs_black()
    m = m.replace(":", "-")
    return m in str(b)


def is_mac_in_orange(m):
    o = macs_orange()
    m = m.replace(":", "-")
    return m in str(o)
