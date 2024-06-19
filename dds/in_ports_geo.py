import json

import requests

from dds.notifications import notify_ddh_in_port
from dds.timecache import is_it_time_to, query_is_it_time_to, its_time_to_so_annotate_it
from utils.ddh_config import dds_get_cfg_skip_dl_in_port_en
from utils.logs import lg_gps as lg


g_last_in_port = False


def dds_ask_in_port_to_ddn(g, notify=True):

    global g_last_in_port
    if dds_get_cfg_skip_dl_in_port_en() == 0:
        # NOT in port when feature not-enabled
        return 0

    s = 'tell_we_in_port'
    if query_is_it_time_to(s):
        # cache, prevent always asking API
        if g_last_in_port:
            # todo ---> remove this when we know it works
            print('in_port = True by cache')
        return g_last_in_port

    # build the query to API
    lat, lon, tg, speed = g
    addr_ddn_api = 'ddn.lowellinstruments.com'
    port_ddn_api = 9000
    ep = 'gps_in_port'
    url = f'http://{addr_ddn_api}:{port_ddn_api}/{ep}?lat={lat}&lon={lon}'

    # send the query
    try:
        rsp = requests.get(url, timeout=5)
        rsp.raise_for_status()
        j = json.loads(rsp.content.decode())
        # j: {'in_port': True}
        g_last_in_port = int(j['in_port'])
        its_time_to_so_annotate_it(s, 120)
        if g_last_in_port:
            lg.a(f'in_port = True by DDN API')
        if notify:
            notify_ddh_in_port(g)
        return g_last_in_port

    except (Exception,) as err:
        lg.a(f'error: dds_ask_in_port_to_ddn request -> {err}')
        # returns FALSE in case no API, so maybe too far away
        lg.a('warning: no API response, consider NOT in port')


if __name__ == '__main__':
    # NO PORT
    g = (-9, -9, None, 1)
    rv = 'in_port_no', dds_ask_in_port_to_ddn(g, notify=False)
    print(rv)
    # ROTARY PORT
    g = (41.609441, -70.608651, None, 1)
    rv = 'in_port_ro', dds_ask_in_port_to_ddn(g, notify=False)
    print(rv)
    # new bedford port
    g = (41.63, -70.91, None, 1)
    rv = 'in_port_nb', dds_ask_in_port_to_ddn(g, notify=False)
    print(rv)
    # sandwich port
    g = (41.771048, -70.503473, None, 1)
    rv = 'in_port_sw', dds_ask_in_port_to_ddn(g, notify=False)
    print(rv)

