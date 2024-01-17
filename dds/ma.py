

def ma(ll, i, w):
    def _m(lt):
        a = 0
        print('lt', lt)
        for t in lt:
            a += t
        print(f'a {a} / len(t) {len(lt)} = {a/len(lt)}')
        return a / len(lt)

    assert w > 0
    e = i + 1 if i + 1 < len(ll) else len(ll)
    s = 0 if w > i else i + 1 - w
    return _m(ll[s:e])


def interesting(ll, i, w):
    if w > i:
        # too soon
        return False
    x = ma(ll, i, w)
    print(f'abs is {abs(x - ll[i])}')
    th = .5
    if abs(x - ll[i]) > th:
        return True


def main():
    ll = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
    print(interesting(ll, 3, 3))



if __name__ == '__main__':
    main()
