import glob
import os
import pathlib
from dds.timecache import is_it_time_to
from mat.data_converter import default_parameters, DataConverter
from mat.data_file_factory import load_data_file
from mat.lix import (
    id_lid_file_flavor, LID_FILE_V1,
    LID_FILE_V2, lid_file_v2_has_sensor_data_type
)
from mat.lix_pr import convert_lix_file
from mat.utils import linux_ls_by_ext
from utils.logs import lg_cnv as lg
from utils.ddh_shared import (
    send_ddh_udp_gui as _u,
    get_ddh_folder_path_dl_files,
    STATE_DDS_NOTIFY_CONVERSION_ERR,
    STATE_DDS_NOTIFY_CONVERSION_OK
)
import pandas as pd

from utils.flag_paths import TMP_PATH_CNV_REQUESTED_VIA_GUI

"""
code in this file only takes care of LID data files
"""


PERIOD_CNV_SECS = 3600 * 12
BAROMETRIC_PRESSURE_SEA_LEVEL_IN_DECIBAR = 10.1
DDH_BPSL = BAROMETRIC_PRESSURE_SEA_LEVEL_IN_DECIBAR


_g_files_we_cannot_convert = []
_g_files_already_converted = []


def _lid_v1_file_has_sensor_data_type(path, suffix):
    if suffix == '_TDO':
        return
    _map = {
        "_DissolvedOxygen": "DOS",
        "_Temperature": "TMP",
        "_Pressure": "PRS"}
    header = load_data_file(path).header()
    return header.tag(_map[suffix])


def _cnv_lid_file_v1(path, suf):
    f = path
    if id_lid_file_flavor(f) != LID_FILE_V1:
        return
    lg.a(f"converting LID file v1 {f} for suffix {suf}")

    # check v1 file header to skip files w/o this sensor data / suffix
    if not _lid_v1_file_has_sensor_data_type(f, suf):
        lg.a(f'warning: skip conversion, file {f} has no {suf} data')
        return

    # do the v1 conversion
    _params = default_parameters()
    DataConverter(f, _params).convert()
    lg.a(f"OK: converted LID file v1 {f} for suffix {suf}")

    # --------------------------------
    # RN4020: hack for pressure adjust
    # --------------------------------
    if ("_Pressure" in suf) and ("moana" not in f.lower()):
        lg.a("debug: adjusting LI file {}".format(f))
        fp_csv = f[:-4] + "_Pressure.csv"
        df = pd.read_csv(fp_csv)
        c = "Pressure (dbar)"
        df[c] = df["Pressure (dbar)"] - DDH_BPSL
        df[c] = df[c].apply(lambda x: x if x > 0 else 0)
        df.to_csv(fp_csv, index=False)


def _cnv_lid_file_v2(f, suf):
    # f: absolute file path ending in .lid
    if id_lid_file_flavor(f) != LID_FILE_V2:
        return
    if not lid_file_v2_has_sensor_data_type(f, suf):
        return
    lg.a(f"converting LID file v2 {f} suffix {suf}")
    convert_lix_file(f)
    lg.a(f"OK: converted LID file v2 {f} suffix {suf}")


def _cnv_fol_lid(fol, suf) -> list:

    # check folder (ex: dl_files/e5-fc-4e-94-ed-dd) exists
    if not pathlib.Path(fol).is_dir():
        lg.a(f"error: folder {fol} not found")
        return []

    # check suffix (ex: _DissolvedOxygen) exists
    valid_suffixes = ("_DissolvedOxygen", "_Temperature", "_Pressure", "_TDO")
    if suf not in valid_suffixes:
        lg.a(f"error: unknown suffix {suf}")
        return []

    # convert LID files
    global _g_files_we_cannot_convert
    global _g_files_already_converted

    for f in linux_ls_by_ext(fol, "lid"):
        # IGNORE test_files
        if os.path.basename(f).startswith('test'):
            continue

        # IGNORE when CSV files already exists
        f_csv = f"{f.split('.')[0]}{suf}.csv"
        if pathlib.Path(f_csv).is_file():
            if f_csv not in _g_files_already_converted:
                # lg.a(f"skip conversion, CSV file {f_csv} already exists")
                _g_files_already_converted.append(f_csv)
            continue

        # IGNORE when LID file already known as bad
        if f in _g_files_we_cannot_convert:
            continue

        # try to convert this LID file
        try:
            _cnv_lid_file_v1(f, suf)
            _cnv_lid_file_v2(f, suf)

        except (ValueError, Exception) as ex:
            lg.a(f"error: converting file {f}, metric {suf} --> {str(ex)}")
            # add to black list of files
            if f not in _g_files_we_cannot_convert:
                lg.a(f"warning: ignoring file {f} for metric {suf} from now on")
                _g_files_we_cannot_convert.append(f)

    return _g_files_we_cannot_convert


def _cnv_serve():

    # see if someone asked conversions
    forced = os.path.exists(TMP_PATH_CNV_REQUESTED_VIA_GUI)
    if forced:
        lg.a(f'warning: conversion forced via GUI')
        os.unlink(TMP_PATH_CNV_REQUESTED_VIA_GUI)

    # this function does not run always, only from time to time
    if not is_it_time_to("do_some_conversions", PERIOD_CNV_SECS) and not forced:
        return

    # general banner
    lg.a('----------------------------')
    lg.a('cnv_serve sequence started')
    lg.a('----------------------------')

    # iterate mac folders
    fol = str(get_ddh_folder_path_dl_files())
    mac_folders = [f.path for f in os.scandir(fol) if f.is_dir()]
    mac_folders = [f for f in mac_folders if '#' not in f]
    for f in mac_folders:
        # only converts LID files, not BIN or anything
        for m in ("_DissolvedOxygen", "_Temperature", "_Pressure", "_TDO"):
            # same file processed for multiple metrics
            _cnv_fol_lid(f, m)

    lg.a('----------------------------')
    lg.a('cnv_serve sequence finished')
    lg.a('----------------------------')

    # GUI update
    if _g_files_we_cannot_convert:
        lg.a(f"error: some files are not converted")
        for f in _g_files_we_cannot_convert:
            lg.a(f"\t- {f}")
        _u(f"{STATE_DDS_NOTIFY_CONVERSION_ERR}")
    else:
        _u(f"{STATE_DDS_NOTIFY_CONVERSION_OK}")


def cnv_serve():
    try:
        _cnv_serve()
    except (Exception, ) as ex:
        e = 'error: conversion exception ex ->'
        if is_it_time_to(e, 3600 * 6):
            lg.a(f'{e} {ex}')


if __name__ == '__main__':
    ff = glob.glob("/tmp/my_bkt_waf/**/*.lid", recursive=True)
    parameters = default_parameters()
    for i, f in enumerate(ff):
        print(f'doing file {i} / {len(ff)} {f}')
        DataConverter(f, parameters).convert()
