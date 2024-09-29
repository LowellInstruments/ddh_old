import datetime
import json
import multiprocessing
import os
import time

import sys
from glob import glob
from multiprocessing import Process

import setproctitle

from dds.gpq import GpqR, FMT_GPQ_TS_FILENAME
from dds.timecache import is_it_time_to
from mat.linux import linux_is_process_running
from utils.ddh_config import ddh_get_cfg_gear_type, dds_get_cfg_gpq_en
from utils.ddh_shared import (get_ddh_folder_path_dl_files,
                              get_ddh_folder_path_gpq_files,
                              TESTMODE_FILENAMEPREFIX)
from utils.logs import lg_cst as lg


MAX_TIME_DIFF_GPS_TRACK_VS_LOGGER_SAMPLE = 30
PATH_LID_CST_ALREADY_PROCESSED = '/tmp/cst_ls_lid_already_processed'


_gr = GpqR()


def _cst_get_mobile_lat_lon_from_dt_s(dt_s_iso: str):
    # dt_s_iso: '2024-05-15T05:43:45.000Z'
    dt_s = dt_s_iso.replace('-', '/')
    # dt_s: '%Y/%m/%d %H:%M:%S.000Z'
    dt_s = dt_s.replace('T', ' ')
    print('\n')
    return _gr.query(dt_s[:-5])


def _purge_old_gpq_json_files():
    # calculate last accepted filename by subtracting from today
    _d = -2
    now = datetime.datetime.now(datetime.timezone.utc)
    now += datetime.timedelta(days=_d)
    fol = get_ddh_folder_path_gpq_files()
    ls = glob(f'{fol}/mobile*.json')
    # filename: mobile_24071216.json
    f = f'{fol}/mobile_{now.strftime(FMT_GPQ_TS_FILENAME)}'
    ls_del = [i for i in ls if i < f]
    for i in ls_del:
        bn = os.path.basename(i)
        lg.a(f'warning: deleting {bn}, older than {_d * -1} days')
        os.unlink(i)


def _create_cst_files():

    if not dds_get_cfg_gpq_en():
        # instead of return prevents zombie processes
        sys.exit(0)

    # 0 normal, 1 trawling
    _gear_type = ddh_get_cfg_gear_type()
    fol = get_ddh_folder_path_dl_files()
    ls_lid = glob(f'{fol}/**/*.lid', recursive=True)

    # save us some work
    ls_lid_already_processed = []
    try:
        with open(PATH_LID_CST_ALREADY_PROCESSED) as f:
            ls_lid_already_processed = f.read().splitlines()
    except (Exception, ) as ex:
        pass

    # ---------------------------------------------------
    # input: GPQ files (JSON) + timestamp from CSV files
    # output: CST files
    # ---------------------------------------------------
    for i_lid in ls_lid:

        if i_lid in ls_lid_already_processed:
            continue

        # avoid test files
        _bn = os.path.basename(i_lid)
        if TESTMODE_FILENAMEPREFIX in _bn:
            # we don't CST process testfiles_
            lg.a(f'warning: skipped and added {_bn} to already processed')
            ls_lid_already_processed.append(i_lid)
            continue

        # be sure we have CSV for this LID file
        f_csv_mask = f'{i_lid[:-4]}*.csv'
        f_csv = glob(f_csv_mask)
        if not f_csv:
            lg.a(f'warning: doing CST but seen no CSV file for {_bn}')
            continue
        f_csv = f_csv[0]

        # infer CST filename from CSV filename
        f_cst = f_csv.replace('.csv', '.cst')
        if os.path.exists(f_cst):
            # CST file already exists, bye
            continue

        # read lines of CSV file
        with open(f_csv, 'r') as fv:
            ll_fv = fv.readlines()
            _bn = os.path.basename(f_csv)
            lg.a(f'generating CST from file {_bn}, {len(ll_fv)} lines')

        # ------------------------------------------------------------------------
        # fixed mode: CST file created with 1 location from fixed_*.json GPQ file
        # ------------------------------------------------------------------------
        if _gear_type == 0:
            f_gpq = f'{get_ddh_folder_path_gpq_files()}/'\
                    f'fixed_{os.path.basename(i_lid[:-4])}.json'
            _bn = os.path.basename(f_gpq)
            if os.path.exists(f_gpq):
                lg.a(f'querying fixed GPQ file {_bn}')
                with open(f_gpq, 'r') as f:
                    d = json.load(f)

                # CST fixed file, GPS location repeated every CSV line
                with open(f_cst, 'w') as ft:
                    ft.write('lat,lon,' + ll_fv[0])
                    for s in ll_fv[1:]:
                        ft.write(f'{d["dl_lat"]},{d["dl_lon"]},' + s)
            else:
                lg.a(f'warning: no fixed GPQ file {_bn}')

        # --------------------------------------------------------------------
        # mobile mode: CST file uses N locations from mobile_*.json GPQ files
        # --------------------------------------------------------------------
        if _gear_type == 1:
            ft = open(f_cst, 'w')
            ft.write('lat,lon,' + ll_fv[0])
            ok_i = 0
            for row in ll_fv[1:]:
                dt_s = row.split(',')[0]

                # CST mobile file, GPS location asked to GPQ DB for every CSV line
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

        # we do not process input files over and over
        _bn = os.path.basename(i_lid)
        lg.a(f'added {_bn} to CST already processed')
        ls_lid_already_processed.append(i_lid)

    # update this file which saves us time
    with open(PATH_LID_CST_ALREADY_PROCESSED, 'w') as f:
        for i in ls_lid_already_processed:
            f.write(i + '\n')


def cst_serve():

    _P_ = "dds_cst"

    def _cst_serve():
        setproctitle.setproctitle(_P_)
        try:
            _purge_old_gpq_json_files()
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
        if is_it_time_to(s, 600):
            # lg.a(s)
            p = Process(target=_cst_serve)
            p.start()


if __name__ == '__main__':
    while 1:
        cst_serve()
        time.sleep(5)
