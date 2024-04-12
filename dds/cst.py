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
from utils.ddh_config import ddh_get_cfg_gear_type
from utils.ddh_shared import get_ddh_folder_path_dl_files, get_ddh_folder_path_gpq_files
from utils.logs import lg_cst as lg


def is_a_tdo_file(p):
    with open(p, 'rb') as f:
        b = f.read()
        print(b[:3])
        return b[:3] == b'TDO'


def tdo_file_has_pfm_1(p):
    pass


_gr = GpqR()


def _cst_get_lat_lon_from_dt_s(dt_s_iso: str):
    # dt_s_iso: '2024-04-04T13:45:31.000'
    dt_s = dt_s_iso.replace('-', '/')
    # dt_s: '%Y/%m/%d %H:%M:%S'
    dt_s = dt_s.replace('T', ' ')
    return _gr.query(dt_s[:-4])


def _create_cst_files():
    fol = get_ddh_folder_path_dl_files()
    ls_lid = glob(f'{fol}/**/*.lid', recursive=True)

    # ---------------
    # main CST loop
    # ---------------
    for i_lid in ls_lid:
        f_csv = glob(f'{i_lid[:-4]}*.csv')[0]
        f_cst = f_csv.replace('.csv', '.cst')
        if not os.path.exists(f_csv):
            # not our job as CST
            continue
        if os.path.exists(f_cst):
            os.unlink(f_cst)
            # already done, bye
            # todo ---> reenable this
            # continue

        # read lines of CSV file
        with open(f_csv, 'r') as fv:
            ll_fv = fv.readlines()
            print(f'debug: file {f_csv} has {len(ll_fv)} lines')

        # CST files generated different depending on gear type
        if ddh_get_cfg_gear_type() == 0:
            # fixed mode: use ONE location in fixed_filename.json GPQ file
            f_gpq = f'{get_ddh_folder_path_gpq_files()}/'\
                    f'fixed_{os.path.basename(i_lid[:-4])}.json'
            # use the info in JSON file to create CST file
            if os.path.exists(f_gpq):
                with open(f_gpq, 'r') as f:
                    d = json.load(f)
                ft = open(f_cst, 'w')
                ft.write('lat,lon,' + ll_fv[0])
                for s in ll_fv[1:]:
                    ft.write(f'{d["dl_lat"]},{d["dl_lon"]},' + s)
                ft.close()

        else:
            # trawling mode: use N locations in dynamic database json GPQ files
            # todo ---> test this
            ft = open(f_cst, 'w')
            ft.write('lat,lon,' + ll_fv[0])
            for row in ll_fv[1:]:
                dt_s = row.split(',')[0]
                index, diff, t_lat_lon = _cst_get_lat_lon_from_dt_s(dt_s)
                print(index, diff, t_lat_lon)
                if index > 0:
                    # 0 means too early
                    t, latlon = t_lat_lon
                    lat, lon = latlon
                    ft.write(f'{lat},{lon},' + row)
                else:
                    ft.write(f',,' + row)
            ft.close()


def cst_serve():
    # ---------------------------------------
    # create CST files from CSV ones
    # ---------------------------------------
    _P_ = "dds_cst"

    def _cst_serve():
        setproctitle.setproctitle(_P_)
        _create_cst_files()
        # instead of return prevents zombie processes
        sys.exit(0)

    # useful to remove past zombie processes
    multiprocessing.active_children()
    if linux_is_process_running(_P_):
        lg.a(f"error: seems last {_P_} took a long time")
    else:
        s = f'launching {_P_}'
        if its_time_to(s, 600):
            lg.a('_' * len(s))
            lg.a(s)
            lg.a('_' * len(s))
            p = Process(target=_cst_serve)
            p.start()


if __name__ == '__main__':
    cst_serve()
