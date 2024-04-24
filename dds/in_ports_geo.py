import json

import requests

from dds.notifications import notify_ddh_in_port
from dds.timecache import its_time_to, check_if_its_time_to
from utils.ddh_config import dds_get_cfg_skip_dl_in_port_en
from utils.logs import lg_gps as lg


def dds_ask_in_port_to_ddn(g):

    if dds_get_cfg_skip_dl_in_port_en() == 0:
        # not in port when this feature not-enabled
        return 0

    lat, lon, tg, speed = g
    s = 'tell_we_in_port'
    if check_if_its_time_to(s):
        # True, we STILL in port, prevent asking again to API
        return 1

    addr_ddn_api = 'ddn.lowellinstruments.com'
    port_ddn_api = 9000
    ep = 'gps_in_port'

    t = 5
    url = f'http://{addr_ddn_api}:{port_ddn_api}/{ep}?lat={lat}&lon={lon}'
    try:
        rsp = requests.get(url, timeout=t)
        rsp.raise_for_status()
        j = json.loads(rsp.content.decode())
        # j: {'in_port': True}
        in_port = int(j['in_port'])
        if in_port and its_time_to(s, 600):
            lg.a(f'warning: we are in port')
            notify_ddh_in_port(g)
        return in_port
    except (Exception,) as err:
        lg.a(f'error: dds_ask_in_port_to_ddn request -> {err}')
        # returns FALSE in case no API, so maybe too far away


if __name__ == '__main__':
    # no port
    rv = 'in_port', dds_ask_in_port_to_ddn(35, -75)
    print(rv)
    # new bedford port
    rv = 'in_port_nb', dds_ask_in_port_to_ddn(41.63, -70.91)
    print(rv)
