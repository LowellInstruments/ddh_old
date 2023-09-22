from functools import lru_cache
from glob import glob
import os
from utils.logs import lg_gra as lg
import pandas as pd
import dateutil.parser as dp
from os.path import basename

from utils.ddh_shared import ddh_get_absolute_application_path


# this contains the full path to mac folder to plot
GRAPH_REQ_JSON_FILE = '/tmp/graph_req.json'


_g_ff_t = []
_g_ff_p = []
_g_ff_do = []


# grab all mac folders
def graph_get_fol_list() -> list:
    """
    get list of absolute paths of "dl_files/<mac>" folders
    """
    d = ddh_get_absolute_application_path() + '/dl_files'
    if os.path.isdir(d):
        f_l = [f.path for f in os.scandir(d) if f.is_dir()]
        # remove 'ddh_vessel' folders
        return [f for f in f_l if "ddh" not in basename(f)]
    return []


# get GRAPH_REQ_JSON_FILE containing the FULL ABSOLUTE folder path to plot
def graph_get_fol_req_file():
    # file written by DDS when requesting a graph
    with open(GRAPH_REQ_JSON_FILE) as f:
        fol = f.read().strip()
    if not os.path.exists(fol):
        e = 'error: {} contains a non-existent graph folder {}'
        lg.a(e.format(GRAPH_REQ_JSON_FILE, fol))
        return
    return fol


def graph_check_fol_req_file():
    return os.path.exists(GRAPH_REQ_JSON_FILE)


def graph_delete_fol_req_file():
    try:
        os.unlink(GRAPH_REQ_JSON_FILE)
    except (Exception, ) as ex:
        lg.a("error: graph_delete_fol_req_file() {}".format(ex))


def graph_set_fol_req_file(mac):
    try:
        with open(GRAPH_REQ_JSON_FILE, "w") as f:
            fol = mac.replace(':', '-')
            dl_files_fol = ddh_get_absolute_application_path() + '/dl_files'
            content = str(dl_files_fol) + '/' + str(fol)
            f.write(content)
    except (Exception, ) as ex:
        lg.a("error: graph_set_fol_req_file() {}".format(ex))


@lru_cache
def graph_get_data_csv(fol, h, hi) -> dict:
    global _g_ff_t, _g_ff_p, _g_ff_do

    _g_ff_t = sorted(glob("{}/{}".format(fol, "*_Temperature.csv")))
    _g_ff_p = sorted(glob("{}/{}".format(fol, "*_Pressure.csv")))
    _g_ff_do = sorted(glob("{}/{}".format(fol, "*_DissolvedOxygen.csv")))
    _g_ff_tap = sorted(glob("{}/{}".format(fol, "*_TAP.csv")))

    # type of haul to plot
    met = ''
    if _g_ff_t:
        if h == 'all':
            _g_ff_t = _g_ff_t
        elif h == 'last':
            _g_ff_t = _g_ff_t[-1:]
        else:
            _g_ff_t = [_g_ff_t[hi]]
    if _g_ff_p:
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

    # check metric is set
    if not met:
        lg.a('error: no metric keys for folder {}'.format(fol))
        return {
            'metric': '',
        }

    # grab values
    s = "graphing\n\tmetric {}\n\tfolder {}\n\thauls {}\n\thi {}"
    lg.a(s.format(met, basename(fol), h, hi))
    if met == 'TP':
        x, t, p = [], [], []
        for f in _g_ff_t:
            lg.a('\tgraph: reading T file {}'.format(basename(f)))
            df = pd.read_csv(f)
            # grab Time (x) values from here
            x += list(df['ISO 8601 Time'])
            t += list(df['Temperature (C)'])
        for f in _g_ff_p:
            lg.a('\tgraph: reading P file {}'.format(basename(f)))
            df = pd.read_csv(f)
            p += list(df['Pressure (dbar)'])

        # convert 2018-11-11T13:00:00.000 --> epoch seconds
        x = [dp.parse('{}Z'.format(i)).timestamp() for i in x]
        return {
            'metric': met,
            'ISO 8601 Time': x,
            'Temperature (C)': t,
            'Pressure (dbar)': p,
        }

    elif met == 'DO':
        x, doc, dot = [], [], []
        for f in _g_ff_do:
            lg.a('\tgraph: reading DO file {}'.format(basename(f)))
            df = pd.read_csv(f)
            x += list(df['ISO 8601 Time'])
            doc += list(df['Dissolved Oxygen (mg/l)'])
            dot += list(df['DO Temperature (C)'])

        # convert dot Celsius to Fahrenheit
        dot = [(c*9/5)+32 for c in dot]

        # convert 2018-11-11T13:00:00.000 --> epoch seconds
        x = [dp.parse('{}Z'.format(i)).timestamp() for i in x]
        return {
            'metric': met,
            'ISO 8601 Time': x,
            'DO Concentration (mg/l)': doc,
            'DO Temperature (F)': dot
        }

    elif met == 'TAP':
        x, tap_t, tap_p, tap_ax, tap_ay, tap_az = [], [], [], [], [], []
        for f in _g_ff_tap:
            lg.a('reading TAP file {}'.format(basename(f)))
            df = pd.read_csv(f, sep=',')
            x += list(df['ISO 8601 Time'])
            tap_t += list(df['Temperature (C)'])
            tap_p += list(df['Pressure (dbar)'])
            tap_ax += list(df['Ax'])
            tap_ay += list(df['Ay'])
            tap_az += list(df['Az'])

        # todo ---> add this when we are almost done to convert dot Celsius to Fahrenheit
        # tap_t = [(c*9/5)+32 for c in tap_t]

        # convert 2018-11-11T13:00:00.000 --> epoch seconds
        x = [dp.parse('{}Z'.format(i)).timestamp() for i in x]
        return {
            'metric': met,
            'ISO 8601 Time': x,
            'Temperature (C)': tap_t,
            'Pressure (dbar)': tap_p,
            'Ax': tap_ax,
            'Ay': tap_ay,
            'Az': tap_az
        }

    else:
        lg.a('error: graph_get_all_csv() unknown metric {}'.format(met))
        assert False
