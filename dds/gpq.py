import bisect
import glob
import os
import time
from datetime import datetime, timedelta
from os.path import basename

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
        p = f'{get_ddh_folder_path_gpq_files()}/{f}'
        os.makedirs(os.path.dirname(p), exist_ok=True)
        dt_s = dt.strftime(FMT_RECORD)
        print(f'W using {f}, add {dt_s}')
        self.db.load(f)
        self.db.add({'t': dt_s, 'lat': lat, 'lon': lon})
        self.db.commit(p)


class GpqR:
    def __init__(self):
        self.db = DB(keys=['t', 'lat', 'lon'])
        self.ls = []
        self.all = {}

    def _load(self, dt: datetime):
        f = dt.strftime(FMT_FILENAME)
        p = f'{get_ddh_folder_path_gpq_files()}/{f}'
        if not os.path.exists(p):
            print(f'R error {basename(p)} file does not exist')
            return
        if f in self.ls:
            print(f'R warning {basename(p)} already loaded')
            return
        self.db.load(p)
        _rr = self.db.get_all().values()
        print(f'R loading {basename(p)}, {len(_rr)} rows')
        d = {r['t']: (r['lat'], r['lon']) for r in _rr}
        self.all.update(d)
        self.ls.append(f)

    def query(self, s):
        # s: '2024/04/05 21:45:22'
        dt_s = datetime.strptime(s, FMT_RECORD)
        self._load(dt_s)
        t = list(self.all.keys())
        if not t:
            # our big dictionary has no values
            return -1, -1, None
        print(f'R query {s} within t0 {t[0]} t-1 {t[-1]} range')
        print(f'\tt has {len(t)} rows')
        i = bisect.bisect_right(t, s)
        if i == 0:
            print(f'\tvalue {s} is too early')
            return 0, -1, None
        if i >= len(t):
            print(f'\tvalue {s} is later, but may still be OK')
        else:
            print(f'\tvalue {s} is in-range')
        now = datetime.strptime(s, FMT_RECORD)
        bef = datetime.strptime(t[i - 1], FMT_RECORD)
        _diff = (now - bef).total_seconds()
        print('\ti', i)
        print('\tdiff ', _diff)
        # get the closest candidate value
        c = list(self.all.items())[i - 1]
        return i, _diff, c


def main_gen_gpq():
    # ------------------------------------------------
    # W test: generate one file lat/lon every second
    # file name is today down to hour
    # ------------------------------------------------
    p = get_ddh_folder_path_gpq_files()
    for i in glob.glob(f'{p}/*.json'):
        print(f'removing file {basename(i)}')
        os.unlink(i)
    print('testing GpqW')
    dn = datetime.now()
    g = GpqW()
    for i in range(0, 1000, 10):
        g.add(datetime.now() + timedelta(seconds=i),
              f'lat{i}', f'lon{i}')

    # useful for debug
    # return

    # ------------------------------------------------
    # R test: in today this hour + prev hour, search
    # for the lat/lon value given 3 time values
    # -------------------------------------------------
    print('testing NGpqR')
    el = time.perf_counter()
    ngr = GpqR()
    a_out_bef = (dn + timedelta(seconds=-500)).strftime(FMT_RECORD)
    a_in = (dn + timedelta(seconds=65)).strftime(FMT_RECORD)
    a_out_aft = (dn + timedelta(seconds=2000)).strftime(FMT_RECORD)
    i, diff = ngr.query(a_out_bef)
    i, diff = ngr.query(a_in)
    i, diff = ngr.query(a_out_aft)
    print('time elapsed NGpqR', time.perf_counter() - el)


if __name__ == '__main__':
    main_gen_gpq()
