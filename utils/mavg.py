verbose = 0


def _p(s):
    if not verbose:
        return
    print(s)


def ma(ll, i, w):
    def mn(lw):
        # mn: mean
        # lw: list windowed
        a = 0
        for x in lw:
            a += x
        _p(f'lw {lw}')
        _p(f'sum {a} / len(lw) {len(lw)} = ma {a / len(lw)}')
        return a / len(lw)

    # ma: moving average
    assert w > 0
    e = i + 1 if i + 1 < len(ll) else len(ll)
    s = 0 if w > i else i + 1 - w
    return mn(ll[s:e])


def ci_ma(ll, i, w, th):
    # ci: condition interesting
    # w: window size
    if w > i:
        # too soon
        return False
    x = ma(ll, i, w)
    _p(f'diff {ll[i]} - ma {x} = {abs(x - ll[i])}\n')
    return abs(x - ll[i]) >= th


def get_interesting_idx_ma(ll, w, th):
    int_ll = [i for i, _ in enumerate(ll) if ci_ma(ll, i, w, th)]
    _p(f'll {ll}')
    _p(f'int_ll {int_ll}')
    return int_ll


def main():
    # ll = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
    ll = [24, 25, 13, 23, 23, 22, 21, 22, 24, 24, 21, 24, 23,
          24, 24, 24, 25, 25, 25, 25, 25, 24, 23, 25, 25, 25,
          26, 26, 26, 25, 25, 26, 26, 26, 25, 26, 28, 24, 27,
          28, 25, 27, 27, 27, 26, 28, 27, 27, 25, 26, 27, 29,
          28, 25, 28, 28, 27, 26, 28, 27, 28, 27, 26, 26, 28,
          27, 26, 27, 27, 27, 27, 28, 28, 28, 26, 27, 25, 28,
          28, 27, 28, 27, 28, 28, 27, 27, 27, 28, 27, 27, 27]
    w = 2
    th = 3
    li = get_interesting_idx_ma(ll, w, th)
    print('li', li)


if __name__ == '__main__':
    main()
