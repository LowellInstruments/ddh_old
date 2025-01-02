import time


dh = {}


def ev_happen_x_times_in_y_seconds(ev, x, y):
    global dh
    start = time.time() - y
    ls = [i for i in dh[ev] if i >= start]
    return len(ls) >= x


def ev_clear(ev):
    global dh
    if ev in dh.keys():
        del dh[ev]


def ev_clear_all():
    global dh
    dh = {}


def ev_add(ev):
    global dh
    if ev not in dh.keys():
        dh[ev] = []
    dh[ev].append(time.time())


if __name__ == '__main__':
    ev_add('a')
    time.sleep(.1)
    ev_add('a')
    time.sleep(1)
    rv = ev_happen_x_times_in_y_seconds('a', x=2 , y=1)
    assert not rv
    rv = ev_happen_x_times_in_y_seconds('a', x=2 , y=2)
    assert rv
    time.sleep(1)
    rv = ev_happen_x_times_in_y_seconds('a', x=2, y=2)
    assert not rv
    print('all ok')


