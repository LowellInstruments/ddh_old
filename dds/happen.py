import time


DEBUG = False
dh = {}


def _p(s):
    if not DEBUG:
        return
    print(s)


def happen_contains(ev):
    return ev in dh.keys()


def happen_n_times_in_last_t_seconds(ev, n, t):
    if not happen_contains(ev):
        return False
    ls = [i for i in dh[ev] if i >= time.perf_counter() - t]
    rv = len(ls) >= n
    if rv:
        print(f'{ev} happened {len(ls)} within the last {t} seconds')
    return rv


def happen_append_to_list(ev):
    global dh
    if not happen_contains(ev):
        dh[ev] = []
    _p(f'** happen_add {ev}')
    dh[ev].append(time.perf_counter())


def happen_set_single_one_as_list(ev):
    global dh
    dh[ev] = [time.perf_counter()]
    _p(f'** happen_one {ev}')


def _happen_show():
    _p('** happen_show')
    for k, v in dh.items():
        _p(f'\t{k}: {v}')


def happen_purge(t, mask=''):
    # a negative purge_seconds value ensures all values selected
    global dh
    _dh_copy = {}
    for k, ls in dh.items():
        if not k.startswith(mask):
            _dh_copy[k] = ls
            continue
        _dh_copy[k] = [v for v in ls if v >= time.perf_counter() - t]
        # remove empty ones
        if not _dh_copy[k]:
            del _dh_copy[k]
    dh = _dh_copy


if __name__ == '__main__':
    happen_append_to_list('ev1')
    time.sleep(1)
    happen_append_to_list('ev2')

    # will NOT remove ev2, too recent
    happen_purge(1, 'ev2')
    _happen_show()

    # will NOT remove ev1, too recent
    happen_purge(1.1, 'ev1')
    _happen_show()

    # will remove ev1, too old
    happen_purge(.9)
    _happen_show()

    # will remove all in fact
    happen_purge(-1)
    _happen_show()
