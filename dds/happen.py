import time


LEN_HISTORY = 25

# dictionary happen
dh = {}


def _happen_clear(k):
    ls_t = [0.0] * LEN_HISTORY
    dh[k] = (0, ls_t)


def happen_add(k):
    t = time.perf_counter()
    if k not in dh.keys():
        i = 1
        ls_t = [0.0] * LEN_HISTORY
        ls_t[0] = t
        dh[k] = (i, ls_t)
    else:
        i = dh[k][0]
        ls_t = dh[k][1]
        ls_t[i] = t
        dh[k] = (((i + 1) % LEN_HISTORY), ls_t)


def happen_n_last_t_secs(k, n, t, can_clear=True):
    assert 0 < n < LEN_HISTORY
    assert t > 0
    if k not in dh.keys():
        return True, 0
    now = time.perf_counter()
    t = now - t
    t = t if t > 0 else 0
    ls_t = dh[k][1]
    ls_t = [i for i in ls_t if t < i <= now]
    rv = (len(ls_t) >= n)
    if rv and can_clear:
        # print(f'_happen_clear, ev {k}')
        _happen_clear(k)
    return rv, len(ls_t)


def happen_is_it_time_to(k, t):
    _, q = happen_n_last_t_secs(k, 1, t, can_clear=False)
    if q == 0:
        happen_add(k)
        return True


if __name__ == "__main__":
    e = 'ev'
    _rv = happen_is_it_time_to(e, .5)
    print(_rv)
    time.sleep(1)
    _rv = happen_is_it_time_to(e, .5)
    print(_rv)
