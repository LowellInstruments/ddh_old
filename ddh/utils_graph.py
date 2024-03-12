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
    _g_ff_t = sorted(glob("{}/{}".format(fol, "*_Temperature.csv")))
    _g_ff_p = sorted(glob("{}/{}".format(fol, "*_Pressure.csv")))
    _g_ff_do = sorted(glob("{}/{}".format(fol, "*_DissolvedOxygen.csv")))
    _g_ff_tap = sorted(glob("{}/{}".format(fol, "*_TDO.csv")))

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
    if _g_ff_do:
        met = 'DO'
        if h == 'all':
            _g_ff_do = _g_ff_do
        elif h == 'last':
            _g_ff_do = _g_ff_do[-1:]
        else:
            _g_ff_do = [_g_ff_do[hi]]
    if _g_ff_tap:
        met = 'TAP'
        if h == 'all':
            _g_ff_tap = _g_ff_tap
        elif h == 'last':
            _g_ff_tap = _g_ff_tap[-1:]
        else:
            _g_ff_tap = [_g_ff_tap[hi]]

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
    tap_t, tap_p, tap_ax, tap_ay, tap_az = [], [], [], [], []
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
        for f in _g_ff_do:
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

    elif met == 'TAP':
        for f in _g_ff_tap:
            lg.a('reading TAP file {}'.format(basename(f)))
            df = cached_read_csv(f)
            x += list(df['ISO 8601 Time'])
            tap_t += list(df['Temperature (C)'])
            tap_p += list(df['Pressure (dbar)'])
            tap_ax += list(df['Ax'])
            tap_ay += list(df['Ay'])
            tap_az += list(df['Az'])

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
    tap_t = tap_t[::n]
    tap_p = tap_p[::n]
    tap_ax = tap_ax[::n]
    tap_ay = tap_ay[::n]
    tap_az = tap_az[::n]

    # Celsius to Fahrenheit
    tf = [(c * 9 / 5) + 32 for c in t]
    dotf = [(c * 9 / 5) + 32 for c in dot]
    tap_tf = [(c * 9 / 5) + 32 for c in tap_t]

    # Depth calculation, convert: f = (dbar - a) * 0.5468
    pf = [(d - CTT_ATM_PRESSURE_DBAR) * .5468 for d in p]
    tap_pf = [(d - CTT_ATM_PRESSURE_DBAR) * .5468 for d in tap_p]
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
        'Temperature (C) TAP': tap_t,
        'Temperature (F) TAP': tap_tf,
        'Pressure (dbar) TAP': tap_p,
        'Depth (fathoms) TAP': tap_pf,
        'Ax TAP': tap_ax,
        'Ay TAP': tap_ay,
        'Az TAP': tap_az,
        'pruned': n != 1,
        'logger_type': lg_t
    }
