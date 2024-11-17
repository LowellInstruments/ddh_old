import bisect
import glob
import json
import os
import time
from datetime import datetime, timedelta
from os.path import basename

from pysondb import DB

from utils.ddh_shared import get_ddh_folder_path_gpq_files

FMT_GPQ_TS_RECORD_DB = '%Y/%m/%d %H:%M:%S'
FMT_GPQ_TS_FILENAME = '%y%m%d%H.json'


# -----------------------------------------------
# Global Position query W/R class,
# ask where local ship was at a certain time
# it returns:
#     - closest time to the queried one
#     - associated position
#     - time diff
# -----------------------------------------------


VERBOSE = False


def _p(s):
    if not VERBOSE:
        return
    print(s)


class GpqW:

    # -----------------------------------------------------------------
    # used by GPS module to record positions on MOBILE mode, not fixed
    # -----------------------------------------------------------------

    def __init__(self):
        self.db = DB(keys=['t', 'lat', 'lon'])

    def add(self, dt: datetime, lat, lon):
        f = 'mobile_' + dt.strftime(FMT_GPQ_TS_FILENAME)
        p = f'{get_ddh_folder_path_gpq_files()}/{f}'
        os.makedirs(os.path.dirname(p), exist_ok=True)
        dt_s = dt.strftime(FMT_GPQ_TS_RECORD_DB)
        # write to existing GPQ file or to new one
        if os.path.exists(p):
            _p(f'GPQ_W: already exists {f}')
            self.db.load(p)
            self.db.add({'t': dt_s, 'lat': lat, 'lon': lon})
        else:
            # don't carry the ones from previous file
            self.db.delete_all()
            # self.db.load(p)
            self.db.add({'t': dt_s, 'lat': lat, 'lon': lon})
        self.db.commit(p)
        _p(f'GPQ_W: add {dt_s} -> {f}')


class GpqR:

    # ----------------------------------------------------
    # used to get gps positions on MOBILE mode, not fixed
    # ----------------------------------------------------

    def __init__(self):
        self.db = DB(keys=['t', 'lat', 'lon'])
        self.ls = []
        self.all = {}

    def _load(self, dt: datetime):

        # infer the database filename
        f = 'mobile_' + dt.strftime(FMT_GPQ_TS_FILENAME)
        p = f'{get_ddh_folder_path_gpq_files()}/{f}'
        _p(f'GPQ_R: value {dt} -> load ask for file {f}')
        if not os.path.exists(p):
            _p(f'GPQ_R: load error -> {basename(p)} file does not exist')
            return
        if f in self.ls:
            _p(f'GPQ_R: load already -> {basename(p)}')
            return

        # load the database filename
        self.db.load(p)
        _rr = self.db.get_all().values()
        _p(f'GPQ_R: load OK -> {len(_rr)} rows from {basename(p)}')
        d = {r['t']: (r['lat'], r['lon']) for r in _rr}
        self.all.update(d)
        self.ls.append(f)

    def query(self, s: str):

        # s: '2024/04/05 21:45:22'
        dt = datetime.strptime(s, FMT_GPQ_TS_RECORD_DB)

        # build dictionary w/ current database and immediately previous one
        self._load(dt)
        dt_bef = dt - timedelta(hours=1)
        self._load(dt_bef)
        t = list(self.all.keys())

        # our built big dictionary does not even have values
        if not t:
            return -1, -1, None
        _p(f'GPQ_R: value query {s}')
        _p(f'GPQ_R: range GPQ DB [ {t[0]} - {t[-1]} ] = {len(t)} rows')
        i = bisect.bisect_right(t, s)

        # value is too early for our big dictionary
        if i == 0:
            _p(f'\tvalue {s} -> pre-range')
            return 0, -1, None

        # value might be useful for calling functions,
        # such as CST, depending on diff
        if i >= len(t):
            _p(f'\tvalue {s} -> post-range')
        else:
            _p(f'\tvalue {s} -> in-range')
        now = datetime.strptime(s, FMT_GPQ_TS_RECORD_DB)
        bef = datetime.strptime(t[i - 1], FMT_GPQ_TS_RECORD_DB)
        _diff = (now - bef).total_seconds()
        _p(f'\ti {i}')
        _p(f'\tdiff {i}')

        # get the closest candidate value
        c = list(self.all.items())[i - 1]
        if i != -1:
            _p(f'\tcandidate {c}')

        # the calling function decides if _diff is ok or too much
        # i: index in array
        # _diff: seconds current time vs. closest one in array
        # c: ('2024/05/14 09:45:39', ('lat990', 'lon990'))
        return i, _diff, c


def gpq_create_fixed_mode_file(g, filename):
    """
    called when downloading loggers on FIXED gear mode
    MOBILE mode, does not use GPQ fixed files
    MOBILE mode, it queries all CSV lines to GPQ database
    ble --> fixed_filename.gpq --> cst_serve
    """
    if not filename.endswith('.lid'):
        return

    lat, lon, tg, speed = g
    d = {
        "dl_lat": lat,
        "dl_lon": lon,
        "dl_utc_tg": str(tg),
        "dl_filename": filename
    }
    fol = str(get_ddh_folder_path_gpq_files())
    path = f"{fol}/fixed_{filename[:-4]}.json"
    with open(path, "w") as fl:
        # from dict to file
        # it has only one entry
        json.dump(d, fl)


def _gpq_gen_test():
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
    a_out_bef = (dn + timedelta(seconds=-500)).strftime(FMT_GPQ_TS_RECORD_DB)
    a_in = (dn + timedelta(seconds=65)).strftime(FMT_GPQ_TS_RECORD_DB)
    a_out_aft = (dn + timedelta(seconds=2000)).strftime(FMT_GPQ_TS_RECORD_DB)
    i, diff, c = ngr.query(a_out_bef)
    i, diff, c = ngr.query(a_in)
    i, diff, c = ngr.query(a_out_aft)
    print(c)
    print('time elapsed NGpqR', time.perf_counter() - el)
