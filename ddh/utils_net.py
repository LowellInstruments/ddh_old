import subprocess as sp
from mat.utils import linux_is_rpi


def net_get_my_current_wlan_ssid() -> str:
    """gets connected wi-fi network name, if any"""

    if linux_is_rpi():
        c = "/usr/sbin/iwgetid -r"
        s = sp.run(c, shell=True, stdout=sp.PIPE)
        return s.stdout.decode().rstrip("\n")

    # when developing
    c = "nmcli -t -f name connection show --active"
    rv = sp.run(c, shell=True, stdout=sp.PIPE)
    if rv.returncode == 0:
        # rv.stdout: b'Candy_Corn\nwg0\n'
        return rv.stdout.decode().split("\n")[0]

    # this may return a command not found error
    c = "iwgetid -r"
    rv = sp.run(c, shell=True, stdout=sp.PIPE)
    if rv.returncode == 0:
        return rv.stdout.decode().rstrip("\n")

    return ""
