import time


DEBUG = False
dh = {}


def _p(s):
    if not DEBUG:
        return
    print(s)


def happen_n_times_in_last_t_seconds(ev, n, t):
    start = time.perf_counter() - t
    return len([i for i in dh[ev] if i >= start]) >= n


def happen_clear_one(ev):
    global dh
    if ev in dh.keys():
        _p(f'** happen_clear_one {ev}')
        del dh[ev]


def happen_clear_all(ev_mask=''):
    global dh
    if not ev_mask:
        _p(f'** happen_clear_all')
        dh = {}
        return
    ls_k = [k for k in dh.keys() if k.startswith(ev_mask)]
    for k in ls_k:
        _p(f'** happen_clear_all with mask {ev_mask}')
        del dh[k]


def happen_add_to_list(ev):
    global dh
    if ev not in dh.keys():
        dh[ev] = []
    _p(f'** happen_add {ev}')
    dh[ev].append(time.perf_counter())


def happen_add_one_as_list(ev):
    global dh
    if ev in dh.keys():
        del dh[ev]
    # list of one
    dh[ev] = [time.perf_counter()]
    _p(f'** happen_one {ev}')


def happen_purge(purge_seconds, ev_mask=''):
    global dh
    _dh_purged = {}
    start_purge = time.perf_counter() - purge_seconds

    # get rid of old values in lists
    for k, ls_v in dh.items():
        _dh_purged[k] = [v for v in ls_v if (v >= start_purge)
                         and k.startswith(ev_mask)]
    if _dh_purged:
        dh = _dh_purged

    # get rid of empty lists
    dh = {k: ls_v for k, ls_v in dh.items() if ls_v}
    _p(f'** happen_post_purge {start_purge}\n\t{dh}')


def _happen_show():
    global dh
    if len(dh) == 0:
        _p('** happen_show_empty')
        return

    _p('** happen_show')
    for k, v in dh.items():
        _p(f'\t{k}: {v}')


def happen_contains(ev):
    global dh
    return ev in dh.keys()


if __name__ == '__main__':
    happen_add_to_list('a')
    time.sleep(1)
    _happen_show()
    happen_purge(2)


