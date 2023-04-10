import bisect
import datetime
import glob
import warnings
from tzlocal import get_localzone
from ddh.db.db_plt import DBPlt
import numpy as np
from dds.cnv import convert_lid_to_csv
import pandas as pd

from utils.ddh_shared import (
    get_mac_from_folder_path,
    ddh_get_is_last_haul,
    ddh_get_db_plots_file,
)
from utils.logs import lg_gui as lg


def _data_offset_minutes(t: str, mm):
    """calculates forward minutes offset"""
    a = datetime.datetime.strptime(t, "%Y-%m-%dT%H:%M:%S.000")
    a += datetime.timedelta(minutes=mm)
    return a.strftime("%Y-%m-%dT%H:%M:%S.000")


def _data_prune_df_older_than(df, csv_column_name, ts):
    try:
        # get ending (e) time
        e = df["ISO 8601 Time"].values[-1]

        # interval, like one hour, one day, one month, in minutes
        # ts: [4, 15, 60, '%H:%M', 1]
        interval = ts[2]

        # adjust (a) time from starting (s) time
        s = _data_offset_minutes(e, -1 * interval)
        a = df["ISO 8601 Time"].values[0]
        if s < a:
            s = a

        # slice it
        df = df[df["ISO 8601 Time"] >= s]
        df = df[df["ISO 8601 Time"] <= e]

        # return time, data series
        return df["ISO 8601 Time"], df[csv_column_name]

    except (KeyError, Exception) as exc:

        lg.a("error: data prune -> {}".format(exc))
        return None, None


def _data_get_csv_column_name_from_metric(m):
    d = {
        "T": "Temperature (C)",
        "P": "Pressure (dbar)",
        "DOS": "Dissolved Oxygen (mg/l)",
        "DOP": "Dissolved Oxygen (%)",
        "DOT": "DO Temperature (C)",
        "WAT": "Water Detect (%)",
    }
    return d[m]


# get csv files -> concat them -> order by time
def _data_csv_files_to_df(files_csv: list):
    try:
        all_csv_rows = [pd.read_csv(f) for f in files_csv]
        df = pd.concat(all_csv_rows, ignore_index=True)
        return df.sort_values(by=["ISO 8601 Time"])

    except (Exception,) as ex:
        lg.a("error: _data_csv_files_to_df -> {}".format(ex))


# data stored as UTC, plotted as localtime
def _data_convert_times_to_my_tz(times: list):
    fmt = "%Y-%m-%dT%H:%M:%S.000"
    tz_ddh = get_localzone()
    tz_utc = datetime.timezone.utc

    out = []
    for s in times:
        dt = datetime.datetime.strptime(s, fmt)
        dt = dt.replace(tzinfo=tz_utc).astimezone(tz=tz_ddh)
        out.append(dt.strftime(fmt))
    return out


# t, d: time, data series
def _data_process_when_no_cache(t, d, ts):
    if t is None:
        return None, None

    # unpack number of slices (= number of ticks in plot)
    # ts: [4, 15, 60, '%H:%M', 1]
    n_slices = ts[0]

    #  unpack duration of slice (= plot resolution)
    mm_slice = ts[1]

    # i -> all timestamps
    i = list(t.values)

    # x -> timestamps of the plot
    # y -> data of the plot
    x, y = [], []

    # slice -> first one, s: start, e: end
    s = i[0]
    e = _data_offset_minutes(s, mm_slice)
    for _ in range(n_slices):
        try:
            # i_x: are indexes, NOT minutes, hours, or whatever
            i_s = bisect.bisect_left(i, s)
            i_e = bisect.bisect_left(i, e)
            sl = d.values[i_s:i_e]

            # v: average ignoring NaNs
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", category=RuntimeWarning)
                v = np.nanmean(sl)
            y.append(v)

        except (KeyError, Exception) as e:
            lg.a("error: when plotting {}".format(e))

        finally:
            # x: representative timestamp for the slice
            x.append(s)

            # proceed to next slice
            s = e
            e = _data_offset_minutes(s, mm_slice)

    return x, y


def data_glob_files_to_plot(fol, ts, metric, suffix, sd):
    c = _data_get_csv_column_name_from_metric(metric)
    mac = get_mac_from_folder_path(fol)

    # ---------------------------------------------
    # generate and GLOB CSV files from LID file
    # ---------------------------------------------

    # todo ---> do we need cnv_serve() function? we already do it here
    convert_lid_to_csv(fol, suffix)
    s = "globbing mask: {}/*{}.csv, metric: {}"
    lg.a(s.format(fol, suffix, metric))
    mask_csv = "{}/*{}.csv".format(fol, suffix)
    files_csv = glob.glob(mask_csv)
    if not files_csv:
        e = "no csv files resulted for searched {}"
        raise Exception(e.format(mask_csv))

    # ---------------------------------------------------
    # how many of these CSV files do we keep in this app
    # ---------------------------------------------------

    lhf = ddh_get_is_last_haul()
    if lhf:
        files_csv = list(files_csv[-1])

    # -------------------------------------------------------
    # load csv files into pandas dataframe and prune by 'ts'
    # -------------------------------------------------------

    df = _data_csv_files_to_df(files_csv)
    x, y = _data_prune_df_older_than(df, c, sd[ts])
    s, e = x.values[0], x.values[-1]

    # ------------------------------
    # pull data from cache... maybe
    # ------------------------------

    p = str(ddh_get_db_plots_file())
    db = DBPlt(p)
    i = "{}({}) for {}"
    if db.does_cache_record_exist(mac, s, e, ts, c):
        _ = "debug: plot cache hit on {}"
        lg.a(_.format(i.format(metric, ts, mac)))
        r_id = db.get_record_id(mac, s, e, ts, c)
        t = db.get_record_times(r_id)
        y_avg = db.get_record_values(r_id)
        return t, y_avg

    # ---------------------------------------------------------
    # no luck with cache, process data and cache it for future
    # ---------------------------------------------------------

    _ = "debug: plot cache miss on {}"
    lg.a(_.format(i.format(metric, ts, mac)))
    t, y_avg = _data_process_when_no_cache(x, y, sd[ts])
    t = _data_convert_times_to_my_tz(t)
    db.add_record(mac, s, e, ts, c, t, y_avg)
    return t, y_avg
