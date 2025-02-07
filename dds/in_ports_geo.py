import json
import time
import requests
from dds.notifications_v2 import notify_ddh_in_port
from dds.timecache import annotate_time_this_occurred, is_it_time_to
from utils.ddh_config import dds_get_cfg_skip_dl_in_port_en
from utils.logs import lg_gps as lg


g_last_in_port = False
TIMEOUT_CACHE_IN_PORT_SECS = 300


def dds_ask_in_port_to_ddn(_g, notify=True, tc=TIMEOUT_CACHE_IN_PORT_SECS):

    if dds_get_cfg_skip_dl_in_port_en() == 0:
        # NOT in port when feature not-enabled
        return 0

    global g_last_in_port
    s = 'tell_we_in_port'
    if not is_it_time_to(s, tc, annotate=False):
        # use our cache to avoid repeated queries
        return g_last_in_port

    # build the query to API
    lat, lon, tg, speed = _g
    if not lat:
        # NOT in port on error 'lat'
        return 0
    addr_ddn_api = 'ddn.lowellinstruments.com'
    port_ddn_api = 9000
    ep = 'gps_in_port'
    url = f'http://{addr_ddn_api}:{port_ddn_api}/{ep}?lat={lat}&lon={lon}'

    # send the query
    try:
        rsp = requests.get(url, timeout=3)
        rsp.raise_for_status()
        j = json.loads(rsp.content.decode())
        # j: {'in_port': True}
        g_last_in_port = int(j['in_port'])
        annotate_time_this_occurred(s, tc)
        if g_last_in_port and notify:
            if is_it_time_to('notify_we_in_port', 43200):
                notify_ddh_in_port(_g)
        return g_last_in_port

    except (Exception,) as err:
        lg.a(f'error: querying DDN API about lat {lat}, lon {lon} -> {err}')
        lg.a('warning: no API response, consider NOT in port')


# ------
# test
# ------
if __name__ == '__main__':

    # NO PORT
    g = (-9, -9, None, 1)
    rv = 'in_port_no', dds_ask_in_port_to_ddn(g, notify=False, tc=1)
    print(rv)

    # simulate to expire cache
    time.sleep(1.1)

    # ROTARY PORT
    g = (41.609441, -70.608651, None, 1)
    rv = 'in_port_ro', dds_ask_in_port_to_ddn(g, notify=False, tc=0)
    print(rv)

    # new bedford port
    g = (41.63, -70.91, None, 1)
    rv = 'in_port_nb', dds_ask_in_port_to_ddn(g, notify=False, tc=0)
    print(rv)

    # sandwich port
    g = (41.771048, -70.503473, None, 1)
    rv = 'in_port_sw', dds_ask_in_port_to_ddn(g, notify=False, tc=0)
    print(rv)

    # error
    g = (41.6101, -70.6093, None, 1)
    rv = 'in_port_er', dds_ask_in_port_to_ddn(g, notify=False, tc=0)
    print(rv)
