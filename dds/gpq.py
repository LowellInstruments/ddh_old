import bisect
import glob
import os
import time
from datetime import datetime, timedelta
from pysondb import DB

from utils.ddh_shared import get_ddh_folder_path_gpq_files

FMT_FILENAME = '%y%m%d%H.json'
FMT_RECORD = '%Y/%m/%d %H:%M:%S'

# -----------------------------------------------
# Global Position query W/R class
# you can ask it where the local ship was
# on a certain time; it returns the closest
# time and its associated position and diff
# between both time values
# -----------------------------------------------


def dds_create_folder_gpq():
    r = get_ddh_folder_path_gpq_files()
    os.makedirs(r, exist_ok=True)


class GpqW:
    def __init__(self):
        self.db = DB(keys=['t', 'lat', 'lon'])

    def add(self, dt: datetime, lat, lon):
        f = dt.strftime(FMT_FILENAME)
        dt_s = dt.strftime(FMT_RECORD)
        print(f'W using {f}')
        self.db.load(f)
        self.db.add({'t': dt_s, 'lat': lat, 'lon': lon})
        p = f'{get_ddh_folder_path_gpq_files()}/{f}'
        os.makedirs(os.path.dirname(p), exist_ok=True)
        self.db.commit(p)


class GpqR:
    def __init__(self, dt: datetime):
        self.f = dt.strftime(FMT_FILENAME)
        print(f'R target {self.f}')
        self.db = DB(keys=['t', 'lat', 'lon'])

    def get_all(self):
        if os.path.exists(self.f):
            self.db.load(self.f)
            _rr = self.db.get_all().values()
            print(f'R loading {self.f}, {len(_rr)} rows')
            d = {r['t']: (r['lat'], r['lon']) for r in _rr}
            return d
        else:
            print(f'R loading {self.f} ERROR NO exists')
            return {}


class NGpqR:
    def __init__(self):
        self.db = DB(keys=['t', 'lat', 'lon'])
        self.ls = []
        self.all = {}

    def load(self, dt: datetime):
        f = dt.strftime(FMT_FILENAME)
        p = f'{get_ddh_folder_path_gpq_files()}/{f}'
        if not os.path.exists(p):
            print(f'R error {p} file does not exist')
            return
        if f in self.ls:
            print(f'R error {p} already loaded')
            return
        self.db.load(p)
        _rr = self.db.get_all().values()
        print(f'R loading {p}, {len(_rr)} rows')
        d = {r['t']: (r['lat'], r['lon']) for r in _rr}
        self.all.update(d)
        self.ls.append(f)

    def query(self, s):
        # s: '2024/04/05 21:45:22'
        dt_s = datetime.strptime(s, FMT_RECORD)
        self.load(dt_s)
        t = list(self.all.keys())
        if not t:
            # our big dictionary has no values
            return 0, 0
        print(f'searching {s} in t0 {t[0]} t-1 {t[-1]} range')
        print(f't has {len(t)} rows')
        i = bisect.bisect_right(t, s)
        if i == 0:
            print(f'\tvalue {s} is too early')
            return 0, 0
        if i >= len(t):
            print(f'\tvalue {s} is later, but may still be OK')
        else:
            print(f'\tvalue {s} is in-range')
        now = datetime.strptime(s, FMT_RECORD)
        bef = datetime.strptime(t[i - 1], FMT_RECORD)
        _diff = (now - bef).total_seconds()
        print('\ti', i)
        print('\tdiff ', _diff)
        return i, _diff


# class NGpqR:
#     def __init__(self, dt: datetime):
#         # now, pre, all
#         self.grn = GpqR(dt)
#         self.grp = GpqR(dt - timedelta(hours=1))
#         self.rrn = self.grn.get_all()
#         self.rrp = self.grp.get_all()
#         # build a big dict
#         self.rra = {}
#         self.rra.update(self.rrp)
#         self.rra.update(self.rrn)
#
#     def load(self, dt: datetime):
#         if dt.strftime(FMT_FILENAME) == self.grn.f:
#             return
#         print('NGpqR switching')
#         self.__init__(dt)
#
#     def query(self, s):
#         # _s: '2024/04/05 21:45:22'
#         t = list(self.rra.keys())
#         if not t:
#             # our big dictionary has no values
#             return 0, 0
#         print(f'searching {s} in t0 {t[0]} t-1 {t[-1]} range')
#         print(f't has {len(t)} rows')
#         i = bisect.bisect_right(t, s)
#         if i == 0:
#             print(f'\tvalue {s} is too early')
#             return 0, 0
#         if i >= len(t):
#             print(f'\tvalue {s} is later, but may still be OK')
#         else:
#             print(f'\tvalue {s} is in-range')
#         now = datetime.strptime(s, FMT_RECORD)
#         bef = datetime.strptime(t[i - 1], FMT_RECORD)
#         _diff = (now - bef).total_seconds()
#         print('\ti', i)
#         print('\tdiff ', _diff)
#         return i, _diff


def main():
    # ------------------------------------------------
    # W test: generate one file lat/lon every second
    # file name is today down to hour
    # ------------------------------------------------
    for i in glob.glob('*.json'):
        os.unlink(i)
    print('testing GpqW')
    dn = datetime.now()
    g = GpqW()
    g.load(dn)
    for i in range(1000):
        g.add(datetime.now() + timedelta(seconds=i),
              f'lat{i}', f'lon{i}')
    g.close()

    # ------------------------------------------------
    # R test: in today this hour + prev hour, search
    # for the lat/lon value given 3 time values
    # -------------------------------------------------
    print('testing NGpqR')
    el = time.perf_counter()
    ngr = NGpqR(dn)
    # superfluous, just to test flexibility
    ngr.load(dn + timedelta(days=1))
    a_out_bef = (dn + timedelta(seconds=-500)).strftime(FMT_RECORD)
    a_in = (dn + timedelta(seconds=100)).strftime(FMT_RECORD)
    a_out_aft = (dn + timedelta(seconds=2000)).strftime(FMT_RECORD)
    i, diff = ngr.query(a_out_bef)
    i, diff = ngr.query(a_in)
    i, diff = ngr.query(a_out_aft)
    print('time elapsed NGpqR', time.perf_counter() - el)


if __name__ == '__main__':
    main()
