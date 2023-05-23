import glob
import os
from mat.utils import linux_is_rpi
import pandas as pd
import dateutil.parser as dp


_g_ff_t = []
_g_ff_p = []
_g_ff_do = []


def graph_get_fol_list():
    """
    return absolute paths of "dl_files/<mac>" folders
    """
    d = '/home/pi/ddh/dl_files'
    if not linux_is_rpi():
        d = '/home/kaz/PycharmProjects/ddh/dl_files'

    if os.path.isdir(d):
        f_l = [f.path for f in os.scandir(d) if f.is_dir()]
        # remove 'ddh_vessel' folders
        return [f for f in f_l if "ddh" not in os.path.basename(f)]
    return []


def graph_get_fol_req_file():
    """
    read file in /tmp containing folder to graph
    """
    try:
        # file written by DDH plot request
        with open('/tmp/graph_req.json') as f:
            fol = f.read().strip()
        if not os.path.exists(fol):
            print('graph: error _at_boot, bad_fol {}'.format(fol))
            os._exit(1)
        return fol
    except (Exception, ) as ex:
        print('graph: error _at_boot, exception', ex)
        os._exit(1)


def graph_get_all_data_csv(fol, lh) -> dict:
    global _g_ff_t, _g_ff_p, _g_ff_do
    met = "TP"
    _g_ff_t = sorted(glob.glob("{}/{}".format(fol, "*_Temperature.csv")))
    _g_ff_p = sorted(glob.glob("{}/{}".format(fol, "*_Pressure.csv")))
    _g_ff_do = sorted(glob.glob("{}/{}".format(fol, "*_DissolvedOxygen.csv")))
    print('graph: trying met {} fol {}'.format(met, fol))

    # last haul stuff
    if _g_ff_t and lh:
        _ = list()
        _.append(_g_ff_t[-1])
        _g_ff_t = _
    if _g_ff_p and lh:
        _ = list()
        _.append(_g_ff_p[-1])
        _g_ff_p = _
    if _g_ff_do and lh:
        _ = list()
        _.append(_g_ff_do[-1])
        _g_ff_do = _

    t, p, x = [], [], []
    if met == 'TP':
        # Temperature values
        if not _g_ff_t:
            print('no _g_ff_t')
        else:
            for f in _g_ff_t:
                print('loading file', f)
                df = pd.read_csv(f)
                # grab Time (x) values from here
                x += list(df['ISO 8601 Time'])
                t += list(df['Temperature (C)'])

        # Pressure values
        if not _g_ff_p:
            print('no _g_ff_p')
        else:
            for f in _g_ff_p:
                print('loading file', f)
                df = pd.read_csv(f)
                p += list(df['Pressure (dbar)'])

        # convert time
        x = [dp.parse('{}Z'.format(i)).timestamp() for i in x]
        return {'ISO 8601 Time': x,
                'Temperature (C)': t,
                'Pressure (dbar)': p}

    elif met == 'DO':
        print('hola')

    else:
        print('wtf _graph_get_all_csv')
        assert False
