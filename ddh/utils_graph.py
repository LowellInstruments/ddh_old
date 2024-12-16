import os
import pathlib
import time
from functools import lru_cache
from glob import glob
from os.path import basename
import numpy as np
import dateutil.parser as dp
import pandas as pd
from utils.ddh_config import dds_get_cfg_flag_graph_test_mode
from utils.ddh_shared import (
    get_ddh_folder_path_dl_files,
    get_dl_folder_path_from_mac,
    TESTMODE_FILENAME_PREFIX
)
from utils.logs import lg_gra as lg
from utils.flag_paths import TMP_PATH_GRAPH_REQ_JSON
from utils.units import dbar_to_fathoms

CTT_ATM_PRESSURE_DBAR = 10.1325

d_last_haul_index = {
    # fol: haul_index
}


def _gfm_build_filename_wc(path):
    # wc: water column, legacy versions called fast (profiling) mode graph (fmg)
    bn = '._' + os.path.basename(path)[:-4] + '.fmg'
    return f'{os.path.dirname(path)}/{bn}'


def _gfm_build_filename_no_wc(path):
    # legacy: old slow (no profiling) mode graph (smg) files w/o water column data
    bn = '._' + os.path.basename(path)[:-4] + '.smg'
    return f'{os.path.dirname(path)}/{bn}'


def utils_graph_classify_file_wc_mode(p):
    # p: full path
    p = str(p)
    bn = os.path.basename(p)
    _is_tdo = p.endswith('_TDO.csv')
    _is_dox = p.endswith('_DissolvedOxygen.csv')
    if not _is_tdo and not _is_dox:
        lg.a('error: bad file to set water column mode')
        return False

    # early leave when "cache" hit
    f_wc = _gfm_build_filename_wc(p)
    f_nowc = _gfm_build_filename_no_wc(p)
    if os.path.exists(f_wc):
        return True
    if os.path.exists(f_nowc):
        return False

    # process new file, read header line
    try:
        with open(p) as f:
            h = f.readline()
    except (Exception, ) as ex:
        lg.a(f'error: reading header in file {bn} -> {ex}')

    # decision for DO-1 loggers
    if _is_dox and 'Water' not in h:
        lg.a(f'graph water column mode: ON for DO-1 file {bn}')
        pathlib.Path(f_wc).touch()
        return True

    # decision for DO-2 loggers, water is last column
    if _is_dox and 'Water' in h:
        lg.a(f'debug: processing water column mode for DO-2 file {bn}')
        with open(p) as f:
            ll = f.readlines()
        for i in ll[3:]:
            w_cur = float(i.split(',')[-1])
            if w_cur > 50:
                lg.a(f'graph water column mode: ON for DO-2 file {bn}')
                pathlib.Path(f_wc).touch()
                return True

        lg.a(f'graph water column mode: OFF for DO-2 file {bn}')
        pathlib.Path(f_nowc).touch()
        return False

    # decision for TDO loggers, check pressure threshold
    if _is_tdo:
        lg.a(f'debug: processing water column mode for TDO file {bn}')
        df = _utils_graph_cached_read_csv(p)
        # df_iw: dataframe of values in water
        df_iw = df[df['Pressure (dbar)'] > 12]
        been_in_water = len(df_iw) > 0
        if been_in_water:
            lg.a(f'graph water column mode: ON for TDO file {bn}')
            pathlib.Path(f_wc).touch()
            return True

        lg.a(f'graph water column mode: OFF for TDO file {bn}')
        pathlib.Path(f_nowc).touch()
        return False

    lg.a(f'error: _utils_graph_classify_file_wc_mode for unknown file {p}')


def utils_graph_get_abs_fol_list() -> list:
    """
    get list of absolute paths of "dl_files/<mac>" folders
    """
    d = str(get_ddh_folder_path_dl_files())
    if dds_get_cfg_flag_graph_test_mode():
        fol_ls = [
            d + '/11-22-33-44-55-66',
            d + '/00-00-00-00-00-00',
            d + '/99-99-99-99-99-99',
            d + '/55-55-55-55-55-55',
            d + '/33-33-33-33-33-33',
        ]
        return fol_ls

    if os.path.isdir(d):
        f_l = [f.path for f in os.scandir(d) if f.is_dir()]
        # remove 'ddh_vessel' folders
        return [f for f in f_l if "ddh" not in basename(f)]
    return []


def utils_graph_read_fol_req_file():
    """
    reads TMP_PATH_GRAPH_REQ_JSON to get ABSOLUTE folder path to graph
    """
    if dds_get_cfg_flag_graph_test_mode():
        return

    # file written by DDS_BLE when requesting a graph
    with open(TMP_PATH_GRAPH_REQ_JSON) as f:
        fol = f.read().strip()
    if not os.path.exists(fol):
        lg.a(f'error: {fol} indicated in {TMP_PATH_GRAPH_REQ_JSON} does not exist')
        return

    return fol


def utils_graph_does_exist_fol_req_file():
    if dds_get_cfg_flag_graph_test_mode():
        return
    return os.path.exists(TMP_PATH_GRAPH_REQ_JSON)


def utils_graph_delete_fol_req_file():
    if dds_get_cfg_flag_graph_test_mode():
        return
    try:
        os.unlink(TMP_PATH_GRAPH_REQ_JSON)
    except (Exception, ) as ex:
        lg.a(f"error: graph_delete_fol_req_file() {ex}")


def utils_graph_set_fol_req_file(mac):
    if dds_get_cfg_flag_graph_test_mode():
        lg.a('warning: not using graph_req_json file but test ones')
        return
    try:
        with open(TMP_PATH_GRAPH_REQ_JSON, "w") as f:
            content = str(get_dl_folder_path_from_mac(mac))
            f.write(content)
    except (Exception, ) as ex:
        lg.a(f"error: graph_set_fol_req_file() {ex}")


def _data_get_prune_period(x, met):
    if len(x) > 6000:
        lg.a(f'data pruning: faster graph for {met}')
        return int(len(x) / 600)
    return 1


@lru_cache(maxsize=512)
def _utils_graph_cached_read_csv(f):
    df = pd.read_csv(f)
    if df.empty:
        lg.a(f'warning: no data for file {f}')
    return df


def utils_graph_fetch_csv_data(
        fol,
        htv,    # htt: haul time view, 'all', 'last', 'single'
        pressed_haul_next
) -> dict:

    # grab all CSV files for all metrics for this folder
    _g_ff_t = sorted(glob(f"{fol}/*_Temperature.csv"))
    _g_ff_p = sorted(glob(f"{fol}/*_Pressure.csv"))
    _g_ff_dot = sorted(glob(f"{fol}/*_DissolvedOxygen.csv"))
    _g_ff_tdo = sorted(glob(f"{fol}/*_TDO.csv"))
    n_tdo_pre_test = len(_g_ff_tdo)

    # don't plot files starting with testfile_
    _g_ff_t = [i for i in _g_ff_t if TESTMODE_FILENAME_PREFIX not in i]
    _g_ff_p = [i for i in _g_ff_p if TESTMODE_FILENAME_PREFIX not in i]
    _g_ff_dot = [i for i in _g_ff_dot if TESTMODE_FILENAME_PREFIX not in i]
    _g_ff_tdo = [i for i in _g_ff_tdo if TESTMODE_FILENAME_PREFIX not in i]

    # exclude TDO files which are too small (~50 bytes per line)
    _filter_tdo_by_size = []
    for i in _g_ff_tdo:
        if os.path.getsize(i) > 1024:
            _filter_tdo_by_size.append(i)
        else:
            lg.a(f'warning: discarded TDO file {os.path.basename(i)} < 1024 bytes')
    _g_ff_tdo = _filter_tdo_by_size

    # include any file NOT having a NO_WC flag
    _g_ff_tdo_wc = [i for i in _g_ff_tdo
                    if not os.path.exists(_gfm_build_filename_no_wc(i))]
    _g_ff_dot_wc = [i for i in _g_ff_dot
                    if not os.path.exists(_gfm_build_filename_no_wc(i))]

    # debug: show them
    # for i in _g_ff_tdo:
        # print(os.path.basename(i), os.path.getsize(i))

    # fast leaving case for TDO loggers
    if n_tdo_pre_test and not _g_ff_tdo:
        e = f'error: no real data yet, disable test mode with DDC'
        lg.a(e)
        return {'error': e}

    # error moana
    # MOANA_0744_99_240221160010_Temperature.csv
    # MOANA_0744_100_240221170632_Temperature.csv
    # MOANA_0744_101_240221181608_Temperature.csv
    # gives order 100, 101, 99 instead of 99, 100, 101
    is_moana = False
    for i in _g_ff_t:
        if 'moana' in os.path.basename(i).lower():
            is_moana = True
    if is_moana:
        _g_ff_t = sorted(_g_ff_t, key=lambda x: os.path.basename(x).split('_')[3])
        _g_ff_p = sorted(_g_ff_p, key=lambda x: os.path.basename(x).split('_')[3])

    # get number of hauls
    nh = max(len(_g_ff_t),
             len(_g_ff_p),
             len(_g_ff_dot),
             len(_g_ff_tdo))

    # calculate haul index
    hi = -1
    if fol not in d_last_haul_index.keys():
        d_last_haul_index[fol] = -1
    if pressed_haul_next:
        d_last_haul_index[fol] = (d_last_haul_index[fol] - 1) % nh
        hi = d_last_haul_index[fol]
        lg.a(f'asked haul #{hi} / {nh} for folder {fol}')

    # type of haul to graph
    met = ''
    if _g_ff_t:
        met = 'TP'
        if htv == 'all':
            _g_ff_t = _g_ff_t
        elif htv == 'last':
            _g_ff_t = _g_ff_t[-1:]
        else:
            _g_ff_t = [_g_ff_t[hi]]
    if _g_ff_p:
        met = 'TP'
        if htv == 'all':
            _g_ff_p = _g_ff_p
        elif htv == 'last':
            _g_ff_p = _g_ff_p[-1:]
        else:
            _g_ff_p = [_g_ff_p[hi]]
    if _g_ff_dot:
        met = 'DO'
        if htv == 'all':
            _g_ff_dot = _g_ff_dot
        elif htv == 'last':
            _g_ff_dot = _g_ff_dot[-1:]
        else:
            _g_ff_dot = [_g_ff_dot[hi]]
    if _g_ff_tdo:
        met = 'TDO'
        if htv == 'all':
            _g_ff_tdo = _g_ff_tdo
        elif htv == 'last':
            _g_ff_tdo = _g_ff_tdo[-1:]
        else:
            _g_ff_tdo = [_g_ff_tdo[hi]]

    # check
    if not met:
        lg.a(f'error: no metric keys to graph folder {fol}')
        return {}

    # summary
    rv: dict
    s = "graph parameters:\n\tmetric {}\n\tfolder {}\n\thauls {}\n\thi {}"
    lg.a(s.format(met, basename(fol), htv, hi))

    # calculate time performance of data-grabbing procedure
    start_ts = time.perf_counter()

    # ================
    # read cached CSV
    # ================
    x = []
    t, p, pftm, mpf = [], [], [], []
    doc, dot, wat = [], [], []
    tdo_t, tdo_p, tdo_ax, tdo_ay, tdo_az = [], [], [], [], []
    is_moana = False

    if met == 'TP':
        for f in _g_ff_t:
            lg.a(f'reading T file {basename(f)}')
            df = _utils_graph_cached_read_csv(f)
            x += list(df['ISO 8601 Time'])
            t += list(df['Temperature (C)'])
        for f in _g_ff_p:
            lg.a(f'reading P file {basename(f)}')
            df = _utils_graph_cached_read_csv(f)
            p += list(df['Pressure (dbar)'])
            is_moana = 'MOANA' in f or 'moana' in f

    elif met == 'DO':
        for f in _g_ff_dot:
            bn = os.path.basename(f)
            lg.a(f'reading DO file {bn}')
            df = _utils_graph_cached_read_csv(f)
            x += list(df['ISO 8601 Time'])

            # plot water column files, nice gap others
            if f in _g_ff_dot_wc:
                doc += list(df['Dissolved Oxygen (mg/l)'])
                dot += list(df['DO Temperature (C)'])
                try:
                    wat += list(df['Water Detect (%)'])
                except (Exception, ):
                    pass
            else:
                lg.a(f'warning: file {bn} no-show for water column mode')
                # so when plotting with connect='finite' these don't appear
                # although the space occupied by them is there
                _m = len(list(df['ISO 8601 Time']))
                doc += [np.nan] * _m
                dot += [np.nan] * _m

    elif met == 'TDO':
        for f in _g_ff_tdo:
            bn = os.path.basename(f)
            lg.a(f'reading {met} file {bn}')
            df = _utils_graph_cached_read_csv(f)
            x += list(df['ISO 8601 Time'])

            # plot water column files, nice gap others
            if f in _g_ff_tdo_wc:
                tdo_t += list(df['Temperature (C)'])
                tdo_p += list(df['Pressure (dbar)'])
                tdo_ax += list(df['Ax'])
                tdo_ay += list(df['Ay'])
                tdo_az += list(df['Az'])
            else:
                lg.a(f'warning: file {bn} no-show due to water column mode')
                # so when plotting with connect='finite' these don't display
                # although the space occupied by them is there
                _m = len(list(df['ISO 8601 Time']))
                tdo_t += [np.nan] * _m
                tdo_p += [np.nan] * _m

    # simplify stuff
    if not met:
        lg.a(f'error: graph_get_all_csv() unknown metric {met}')
        return {}

    # things we don't plot
    if len(x) == 1:
        e = f'error: only one data row in file'
        lg.a(e)
        return {'error': e}

    # ----------------------
    # prune data or not
    # ----------------------
    n = _data_get_prune_period(x, met)

    x = x[::n]
    t = t[::n]
    p = p[::n]
    doc = doc[::n]
    dot = dot[::n]
    wat = wat[::n]
    tdo_t = tdo_t[::n]
    tdo_p = tdo_p[::n]
    tdo_ax = tdo_ax[::n]
    tdo_ay = tdo_ay[::n]
    tdo_az = tdo_az[::n]

    # Celsius to Fahrenheit
    tf = [(c * 9 / 5) + 32 for c in t]
    dotf = [(c * 9 / 5) + 32 for c in dot]
    bad_idx = []
    for i_c, c in enumerate(tdo_t):
        if c == '000nan':
            bad_idx.append(i_c)
    for i in bad_idx:
        x.pop(i)
        tdo_t.pop(i)
        tdo_p.pop(i)
        tdo_ax.pop(i)
        tdo_ay.pop(i)
        tdo_az.pop(i)
    tdo_tf = []
    for c in tdo_t:
        tdo_tf.append(((float(c) * 9) /5) + 32)

    # Depth conversion to fathoms ftm
    pftm = [dbar_to_fathoms(d - CTT_ATM_PRESSURE_DBAR) for d in p]
    tdo_pftm = [dbar_to_fathoms(d - CTT_ATM_PRESSURE_DBAR) for d in tdo_p]
    # Moana loggers pressure does not include atm. pressure
    mpf = [d * .5468 for d in p]
    pftm = pftm if not is_moana else mpf

    # convert 2018-11-11T13:00:00.000 --> seconds
    try:
        x = [dp.isoparse(f'{i}Z').timestamp() for i in x]
    except (Exception, ):
        x = [dp.isoparse(f'{i}').timestamp() for i in x]

    # display time performance of data-grabbing procedure
    end_ts = time.perf_counter()
    el_ts = int((end_ts - start_ts) * 1000)
    lg.a(f'data-grabbing {len(x)} {met} points, took {el_ts} ms')

    # decide logger type
    lg_t = met
    lg_t = lg_t if not is_moana else 'Moana'

    # build output dictionary to graph
    return {
        'metric': met,
        'ISO 8601 Time': x,
        'Temperature (C) TP': t,
        'Temperature (F) TP': tf,
        'Pressure (dbar) TP': p,
        'Depth (fathoms) TP': pftm,
        'DO Concentration (mg/l) DO': doc,
        'Temperature (C) DO': dot,
        'Temperature (F) DO': dotf,
        'Water Detect (%) DO': wat,
        'Temperature (C) TDO': tdo_t,
        'Temperature (F) TDO': tdo_tf,
        'Pressure (dbar) TDO': tdo_p,
        'Depth (fathoms) TDO': tdo_pftm,
        'Ax TDO': tdo_ax,
        'Ay TDO': tdo_ay,
        'Az TDO': tdo_az,
        'pruned': n != 1,
        'logger_type': lg_t
    }
