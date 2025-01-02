import time


dh = {}


def happen_n_times_in_last_t_seconds(ev, n, t):
    start = time.time() - t
    return len([i for i in dh[ev] if i >= start]) >= n


def happen_clear(ev):
    global dh
    if ev in dh.keys():
        del dh[ev]


def happen_clear_all():
    global dh
    dh = {}


def happen_add(ev):
    global dh
    if ev not in dh.keys():
        dh[ev] = []
    dh[ev].append(time.time())


if __name__ == '__main__':
    happen_add('a')
    time.sleep(.1)
    happen_add('a')
    time.sleep(1)
    rv = happen_n_times_in_last_t_seconds('a', n=2 , t=1)
    assert not rv
    rv = happen_n_times_in_last_t_seconds('a', n=2 , t=2)
    assert rv
    time.sleep(1)
    rv = happen_n_times_in_last_t_seconds('a', n=2, t=2)
    assert not rv
    print('all ok')


