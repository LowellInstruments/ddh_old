import glob
import os
import pathlib

from dds.timecache import its_time_to
from mat.data_converter import default_parameters, DataConverter
from mat.data_file_factory import load_data_file
from mat.utils import linux_ls_by_ext
from utils.logs import lg_cnv as lg
from utils.ddh_shared import (
    send_ddh_udp_gui as _u,
    get_ddh_folder_path_dl_files,
    STATE_DDS_NOTIFY_CONVERSION_ERR,
    STATE_DDS_NOTIFY_CONVERSION_OK,
)
import pandas as pd


PERIOD_CNV_SECS = 3600 * 12
BAROMETRIC_PRESSURE_SEA_LEVEL_IN_DECIBAR = 10.1
DDH_BPSL = BAROMETRIC_PRESSURE_SEA_LEVEL_IN_DECIBAR


_g_files_we_cannot_convert = []
_g_files_already_exists_told = []


def _lid_file_has_sensor_data_type(path, suffix):
    _map = {"_DissolvedOxygen": "DOS", "_Temperature": "TMP", "_Pressure": "PRS"}
    header = load_data_file(path).header()
    return header.tag(_map[suffix])


def _cnv(fol, suf) -> (bool, list):

    # ---------------------------
    # check asked folder exists
    # fol: dl_files/e5-fc-4e-94-ed-dd
    # ---------------------------

    if not pathlib.Path(fol).is_dir():
        lg.a("error: folder {} not found".format(fol))
        return False, []

    # ---------------------------
    # check asked suffix exists
    # suffix: _DissolvedOxygen
    # ---------------------------

    valid_suffixes = ("_DissolvedOxygen", "_Temperature", "_Pressure", "_WaterDetect")
    if suf not in valid_suffixes:
        lg.a("error: unknown suffix {}".format(suf))
        return False, []

    # needed variables for conversion
    parameters = default_parameters()
    err_files = []
    all_ok = True
    global _g_files_we_cannot_convert
    lid_files = linux_ls_by_ext(fol, "lid")

    # ------------------------------------------------
    # iterate all LID files w/in this logger's folder
    # ------------------------------------------------

    for f in lid_files:

        # do not convert when already have CSV files for this LID file
        _ = "{}{}.csv".format(f.split(".")[0], suf)
        if pathlib.Path(_).is_file():
            global _g_files_already_exists_told
            s = "debug: skip conversion, file {} already exists"
            if _ not in _g_files_already_exists_told:
                lg.a(s.format(_))
                _g_files_already_exists_told.append(_)
            continue

        # do not convert when LID file already known as defective
        if f in _g_files_we_cannot_convert:
            continue

        # -----------------------------
        # try to convert this LID file
        # -----------------------------

        try:

            # skip files not containing this sensor data
            if not _lid_file_has_sensor_data_type(f, suf):
                # s = 'debug: skip conversion, file {} has no {} data'
                # lg.a(s.format(f, suf))
                continue

            DataConverter(f, parameters).convert()
            lg.a("converted file {} for suffix {}".format(f, suf))

            # --------------------------------
            # RN4020: hack for pressure adjust
            # --------------------------------
            if ("_Pressure" in suf) and ("moana" not in f):
                lg.a("debug: adjusting LI file {}".format(f))
                fp_csv = f[:-4] + "_Pressure.csv"
                df = pd.read_csv(fp_csv)
                c = "Pressure (dbar)"
                df[c] = df["Pressure (dbar)"] - DDH_BPSL
                df[c] = df[c].apply(lambda x: x if x > 0 else 0)
                df.to_csv(fp_csv, index=False)

        except (ValueError, Exception) as ex:

            all_ok = False
            err_files.append(f)
            e = "error: converting file {}, metric {} --> {}"
            lg.a(e.format(f, suf, str(ex)))

            # only happens once
            if f not in _g_files_we_cannot_convert:
                e = "warning: ignoring file {} for metric {} from now on"
                lg.a(e.format(f, suf))
                _g_files_we_cannot_convert.append(f)

    return all_ok, err_files


# alias for this function
def convert_lid_to_csv(fol, suf) -> (bool, list):
    return _cnv(fol, suf)


def _cnv_metric(m):
    fol = str(get_ddh_folder_path_dl_files())
    rv, _ = _cnv(fol, m)
    return rv


def cnv_serve():

    # this function does not run always, only from time to time
    if not its_time_to("do_some_conversions", PERIOD_CNV_SECS):
        return

    # general banner
    fol = str(get_ddh_folder_path_dl_files())
    s = "folder: {} | metrics: {}, {}, {}"
    lg.a(s.format(fol, "_DissolvedOxygen", "_Temperature", "_Pressure"))

    # error variable
    e = ""

    # this one includes WATER
    s = "some {} .lid files did not convert"
    m = "_DissolvedOxygen"
    rv = _cnv_metric(m)
    if not rv:
        e += "O"
        lg.a(s.format(m))

    m = "_Temperature"
    rv = _cnv_metric(m)
    if not rv:
        e += "T"
        lg.a(s.format(m))

    m = "_Pressure"
    rv = _cnv_metric(m)
    if not rv:
        e += "P"
        lg.a(s.format(m))

    # GUI update
    if e:
        _u("{}/{}".format(STATE_DDS_NOTIFY_CONVERSION_ERR, e))
    else:
        _u("{}/OK".format(STATE_DDS_NOTIFY_CONVERSION_OK))


if __name__ == '__main__':
    os.chdir('..')
    print('PWD of script conv = ', os.getcwd())
    for each in glob.glob('dl_files/60-77-71-22-c8-4f/*.csv'):
        os.unlink(each)
    convert_lid_to_csv('dl_files/60-77-71-22-c8-4f', '_DissolvedOxygen')
