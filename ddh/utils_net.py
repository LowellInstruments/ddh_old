import subprocess as sp


def net_get_my_current_wlan_ssid() -> str:
    """gets connected wi-fi network name, if any"""

    c = "iwgetid -r"
    s = sp.run(c, shell=True, stdout=sp.PIPE)
    return s.stdout.decode().rstrip("\n")
