import os
import time
from functools import lru_cache
from glob import glob
from os.path import basename
import dateutil.parser as dp
import pandas as pd

from utils.ddh_config import dds_get_cfg_flag_graph_test_mode
from utils.ddh_shared import (get_ddh_folder_path_dl_files,
                              get_dl_folder_path_from_mac)
from utils.logs import lg_gra as lg
from utils.tmp_paths import TMP_PATH_GRAPH_REQ_JSON

CTT_ATM_PRESSURE_DBAR = 10.1325


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
        e = 'error: {} contains a non-existent graph folder {}'
        lg.a(e.format(TMP_PATH_GRAPH_REQ_JSON, fol))
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
        lg.a("error: graph_delete_fol_req_file() {}".format(ex))


def utils_graph_set_fol_req_file(mac):
    if dds_get_cfg_flag_graph_test_mode():
        lg.a('warning: not using graph_req_json file but test ones')
        return
    try:
        with open(TMP_PATH_GRAPH_REQ_JSON, "w") as f:
            content = str(get_dl_folder_path_from_mac(mac))
            f.write(content)
    except (Exception, ) as ex:
        lg.a("error: graph_set_fol_req_file() {}".format(ex))


def _data_build_dict_intervals(df, di) -> dict:
    # shape: (rows, columns)
    n = df.shape[0]
    if n < 2:
        print('discarding')
        return di
    a = df.at[0, 'ISO 8601 Time']
    ta = dp.parse('{}Z'.format(a)).timestamp()
    b = df.at[1, 'ISO 8601 Time']
    tb = dp.parse('{}Z'.format(b)).timestamp()
    delta = tb - ta
    v = n
    if delta in di.keys():
        v = di[delta]
        v += n
    di[delta] = v
    return di


def _data_get_prune_period(x, met):
    if len(x) > 8000:
        lg.a('--------------------------------------')
        lg.a(f'data pruning -> faster graph for {met}')
        lg.a('--------------------------------------')
        return int(len(x) / 600)
    return 1


@lru_cache(maxsize=256)
def cached_read_csv(f):
    df = pd.read_csv(f)
    if df.empty:
        lg.a('warning: no data for file {}'.format(f))
    return df


@lru_cache(maxsize=256)
def process_graph_csv_data(fol, _, h, hi) -> dict:

    # 2nd parameter ignored, only use by lru_cache()
    _g_ff_t = sorted(glob(f"{fol}/*_Temperature.csv"))
    _g_ff_p = sorted(glob(f"{fol}/*_Pressure.csv"))
    _g_ff_dot = sorted(glob(f"{fol}/*_DissolvedOxygen.csv"))
    _g_ff_tdo = sorted(glob(f"{fol}/*_TDO.csv"))

    # type of haul to graph
    met = ''
    if _g_ff_t:
        met = 'TP'
        if h == 'all':
            _g_ff_t = _g_ff_t
        elif h == 'last':
            _g_ff_t = _g_ff_t[-1:]
        else:
            _g_ff_t = [_g_ff_t[hi]]
    if _g_ff_p:
        met = 'TP'
        if h == 'all':
            _g_ff_p = _g_ff_p
        elif h == 'last':
            _g_ff_p = _g_ff_p[-1:]
        else:
            _g_ff_p = [_g_ff_p[hi]]
    if _g_ff_dot:
        met = 'DO'
        if h == 'all':
            _g_ff_dot = _g_ff_dot
        elif h == 'last':
            _g_ff_dot = _g_ff_dot[-1:]
        else:
            _g_ff_dot = [_g_ff_dot[hi]]
    if _g_ff_tdo:
        met = 'TDO'
        if h == 'all':
            _g_ff_tdo = _g_ff_tdo
        elif h == 'last':
            _g_ff_tdo = _g_ff_tdo[-1:]
        else:
            _g_ff_tdo = [_g_ff_tdo[hi]]

    # check
    if not met:
        lg.a('error: no metric keys to graph folder {}'.format(fol))
        return {}

    # summary
    rv: dict
    s = "graph:\n\tmetric {}\n\tfolder {}\n\thauls {}\n\thi {}"
    lg.a(s.format(met, basename(fol), h, hi))

    # calculate time performance of data-grabbing procedure
    start_ts = time.perf_counter()

    # ---------
    # read CSV
    # ---------
    x = []
    t, p, pf, mpf = [], [], [], []
    doc, dot = [], []
    tdo_t, tdo_p, tdo_ax, tdo_ay, tdo_az = [], [], [], [], []
    is_moana = False

    if met == 'TP':
        for f in _g_ff_t:
            lg.a('reading T file {}'.format(basename(f)))
            df = cached_read_csv(f)
            x += list(df['ISO 8601 Time'])
            t += list(df['Temperature (C)'])
        for f in _g_ff_p:
            lg.a('reading P file {}'.format(basename(f)))
            df = cached_read_csv(f)
            p += list(df['Pressure (dbar)'])
            is_moana = 'MOANA' in f or 'moana' in f

    elif met == 'DO':
        di = dict()
        for f in _g_ff_dot:
            lg.a('reading DO file {}'.format(basename(f)))
            df = cached_read_csv(f)
            _ = _data_build_dict_intervals(df, di)
            if not _:
                continue
            di = _
            x += list(df['ISO 8601 Time'])
            doc += list(df['Dissolved Oxygen (mg/l)'])
            dot += list(df['DO Temperature (C)'])
        if not di:
            lg.a('error: NO _data_build_dict_intervals')
            return {}

    elif met == 'TDO':
        for f in _g_ff_tdo:
            lg.a(f'reading {met} file {basename(f)}')
            df = cached_read_csv(f)
            x += list(df['ISO 8601 Time'])
            tdo_t += list(df['Temperature (C)'])
            tdo_p += list(df['Pressure (dbar)'])
            tdo_ax += list(df['Ax'])
            tdo_ay += list(df['Ay'])
            tdo_az += list(df['Az'])

    # simplify stuff
    if not met:
        lg.a('error: graph_get_all_csv() unknown metric {}'.format(met))
        return {}

    # ----------------------
    # prune data or not
    # ----------------------
    n = _data_get_prune_period(x, met)
    x = x[::n]
    t = t[::n]
    p = p[::n]
    doc = doc[::n]
    dot = dot[::n]
    tdo_t = tdo_t[::n]
    tdo_p = tdo_p[::n]
    tdo_ax = tdo_ax[::n]
    tdo_ay = tdo_ay[::n]
    tdo_az = tdo_az[::n]

    # Celsius to Fahrenheit
    tf = [(c * 9 / 5) + 32 for c in t]
    dotf = [(c * 9 / 5) + 32 for c in dot]
    tdo_tf = [(c * 9 / 5) + 32 for c in tdo_t]

    # Depth calculation, convert: f = (dbar - a) * 0.5468
    pf = [(d - CTT_ATM_PRESSURE_DBAR) * .5468 for d in p]
    tdo_pf = [(d - CTT_ATM_PRESSURE_DBAR) * .5468 for d in tdo_p]
    mpf = [d * .5468 for d in p]
    # Moana loggers pressure does not include atm. pressure
    pf = pf if not is_moana else mpf

    # convert 2018-11-11T13:00:00.000 --> seconds
    x = [dp.parse('{}Z'.format(i)).timestamp() for i in x]

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
        'Depth (fathoms) TP': pf,
        'DO Concentration (mg/l) DO': doc,
        'Temperature (C) DO': dot,
        'Temperature (F) DO': dotf,
        'Temperature (C) TDO': tdo_t,
        'Temperature (F) TDO': tdo_tf,
        'Pressure (dbar) TDO': tdo_p,
        'Depth (fathoms) TDO': tdo_pf,
        'Ax TDO': tdo_ax,
        'Ay TDO': tdo_ay,
        'Az TDO': tdo_az,
        'pruned': n != 1,
        'logger_type': lg_t
    }
