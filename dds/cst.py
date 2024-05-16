import json
import multiprocessing
import os
import sys
from datetime import datetime
from glob import glob
from multiprocessing import Process

import setproctitle

from dds.gpq import GpqR, FMT_GPQ_TS_RECORD_DB
from dds.timecache import its_time_to
from mat.linux import linux_is_process_running
from utils.ddh_config import ddh_get_cfg_gear_type, dds_get_cfg_gpq_en
from utils.ddh_shared import (get_ddh_folder_path_dl_files,
                              get_ddh_folder_path_gpq_files)
from utils.logs import lg_cst as lg


MAX_TIME_DIFF_GPS_TRACK_VS_LOGGER_SAMPLE = 30


def is_a_tdo_file(p):
    with open(p, 'rb') as f:
        b = f.read()
        return b[:3] == b'TDO'


def tdo_file_has_pfm_1(p):
    pass


_gr = GpqR()


def _cst_get_mobile_lat_lon_from_dt_s(dt_s_iso: str):
    # dt_s_iso: '2024-05-15T05:43:45.000Z'
    dt_s = dt_s_iso.replace('-', '/')
    # dt_s: '%Y/%m/%d %H:%M:%S.000Z'
    dt_s = dt_s.replace('T', ' ')
    print('\n')
    return _gr.query(dt_s[:-5])


def _create_cst_files():
    fol = get_ddh_folder_path_dl_files()
    ls_lid = glob(f'{fol}/**/*.lid', recursive=True)

    # -----------------------------
    # input: GPQ, aka JSON, files
    # output: CST files
    # -----------------------------
    for i_lid in ls_lid:

        # be sure we have CSV for this LID file
        f_csv = glob(f'{i_lid[:-4]}*.csv')[0]
        if not os.path.exists(f_csv):
            continue

        # infer CST filename from CSV filename
        f_cst = f_csv.replace('.csv', '.cst')
        if os.path.exists(f_cst):
            # this CST file already exists, bye
            continue

        # read lines of CSV file
        with open(f_csv, 'r') as fv:
            ll_fv = fv.readlines()
            lg.a(f'debug: generating CST, file {f_csv} has {len(ll_fv)} lines')

        # fixed mode: CST file uses 1 location from fixed_*.json GPQ file
        f_gpq = f'{get_ddh_folder_path_gpq_files()}/'\
                f'fixed_{os.path.basename(i_lid[:-4])}.json'
        if os.path.exists(f_gpq):
            with open(f_gpq, 'r') as f:
                d = json.load(f)
            ft = open(f_cst, 'w')
            ft.write('lat,lon,' + ll_fv[0])
            for s in ll_fv[1:]:
                ft.write(f'{d["dl_lat"]},{d["dl_lon"]},' + s)
            ft.close()
            continue

        # mobile mode: CST file uses N locations from mobile_*.json GPQ files
        ft = open(f_cst, 'w')
        ft.write('lat,lon,' + ll_fv[0])
        ok_i = 0
        for row in ll_fv[1:]:
            dt_s = row.split(',')[0]
            index, diff, t_lat_lon = _cst_get_mobile_lat_lon_from_dt_s(dt_s)
            if index > 0:
                # -1, means none, 0 means too early
                t, latlon = t_lat_lon
                lat, lon = latlon
                if diff <= MAX_TIME_DIFF_GPS_TRACK_VS_LOGGER_SAMPLE:
                    ft.write(f'{lat},{lon},' + row)
                    ok_i += 1
                else:
                    ft.write(f',,' + row)
                    print(f'CST: discarding {dt_s}')
                    print(f'\tdiff {diff} > {MAX_TIME_DIFF_GPS_TRACK_VS_LOGGER_SAMPLE}')
            else:
                ft.write(f',,' + row)
        print(f'CST: output file has {ok_i} OK complete records')
        ft.close()


def cst_serve():

    if not dds_get_cfg_gpq_en():
        # instead of return prevents zombie processes
        sys.exit(0)

    _P_ = "dds_cst"

    def _cst_serve():
        setproctitle.setproctitle(_P_)
        try:
            _create_cst_files()
        except (Exception, ) as ex:
            lg.a(f'error: CST_serve exception -> {ex}')
        # instead of return prevents zombie processes
        sys.exit(0)

    # useful to remove past zombie processes
    multiprocessing.active_children()
    if linux_is_process_running(_P_):
        lg.a(f"error: seems last {_P_} took a long time")
    else:
        s = f'launching {_P_}'
        # todo: change this CST serve to 600
        if its_time_to(s, 10):
            lg.a('_' * len(s))
            lg.a(s)
            lg.a('_' * len(s))
            p = Process(target=_cst_serve)
            p.start()


if __name__ == '__main__':
    cst_serve()
