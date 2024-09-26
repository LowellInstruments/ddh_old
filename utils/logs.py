import datetime
import glob
import os
from pathlib import Path
from dds.timecache import is_it_time_to
from utils.ddh_config import dds_get_cfg_vessel_name, dds_get_cfg_flag_download_test_mode
from utils.ddh_shared import (
    get_ddh_folder_path_logs,
    get_ddh_folder_path_dl_files, get_ddh_folder_path_lef, TESTMODE_FILENAMEPREFIX,
)
from mat.utils import PrintColors as PC


g_last_tk_ts_unit = None
g_last_file_out = ''
g_last_t = ''


class DDSLogs:
    def __init__(self, label, entity="dds"):
        self.label = label
        self.f_name = self._gen_log_file_name(entity)
        self.enabled = True

    @staticmethod
    def _gen_log_file_name(entity) -> str:
        assert entity in ("dds", "gui")
        d = str(get_ddh_folder_path_logs())
        Path(d).mkdir(parents=True, exist_ok=True)
        now = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        return f"{d}/{entity}_{now}.log"

    def _retrieve_log_file_name(self):
        return self.f_name

    def are_enabled(self, b):
        self.enabled = b
        self.a(f"{self.label.upper()}_logs enabled = {self.enabled}")

    # stands for 'print format'
    def _pf(self, s):
        if type(s) is bytes:
            s = s.decode()

        # color stuff
        if "error" in s:
            PC.R(s)
        elif "debug" in s:
            PC.B(s)
        elif "warning" in s:
            PC.Y(s)
        elif "success" in s:
            PC.G(s)
        elif "OK" in s:
            PC.G(s)
        else:
            PC.N(s)

        return s

    # stands for 'append'
    def a(self, s, show_ts=True):
        if not self.enabled:
            return

        global g_last_t
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        utcnow = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

        # pre-pend date, better logs
        with open(self.f_name, "a") as f:
            if g_last_t != now:
                if show_ts:
                    ts = f"\n\n[ CLK ] {now} / {utcnow}"
                    PC.N(ts)
                    f.write(ts + '\n')
            g_last_t = now
            s = f'[ {self.label.upper()} ] {s}'
            self._pf(s)
            f.write(s + "\n")


lg_dds = DDSLogs("ble")
lg_aws = DDSLogs("aws")
lg_cnv = DDSLogs("cnv")
lg_sns = DDSLogs("sns")
lg_sqs = DDSLogs("sqs")
lg_gps = DDSLogs("gps")
lg_gui = DDSLogs("gui", entity="gui")
lg_net = DDSLogs("net")
lg_emo = DDSLogs("emo")
lg_log = DDSLogs("log")
lg_api = DDSLogs("api")
lg_gra = DDSLogs("gra")
lg_cst = DDSLogs("cst")
lg_gpq = DDSLogs("gpq")
lg_sta = DDSLogs("sta")


# these NORMAL logs are local
def dds_log_core_start_at_boot():

    # create NORMAL log folder if it does not exist
    d = str(get_ddh_folder_path_logs())
    Path(d).mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lg_dds.a(f"started DDS logs on {ts}")


# these TRACKING logs get uploaded
def dds_log_tracking_add(lat, lon, tg):

    if not is_it_time_to("track_boat_gps", t=10):
        return
    if not lat:
        lg_dds.a("error: dds_log_tracking_add() no lat")
        return
    if not tg:
        lg_dds.a("error: dds_log_tracking_add() no tg")
        return

    # works with GPS hat and PUCK, checked
    tg = tg.replace(microsecond=0)
    iso_tg = tg.isoformat()

    # how often filename rotates
    # when testing, change %d (day) to %M (minutes)
    global g_last_tk_ts_unit
    flag_new_file = g_last_tk_ts_unit != tg.strftime("%d")
    g_last_tk_ts_unit = tg.strftime("%d")

    # --------------------------------------------------
    # get current GPS time in our string format, as UTC
    # --------------------------------------------------
    str_iso_tg_tz_utc = '{}Z'.format(iso_tg)

    # create TRACKING log folder if it does not exist
    v = dds_get_cfg_vessel_name().replace(" ", "_")
    d = str(get_ddh_folder_path_dl_files())
    d = f"{d}/ddh#{v}/"
    Path(d).mkdir(parents=True, exist_ok=True)

    # get the filename, either new or re-use previous one
    global g_last_file_out
    file_out = g_last_file_out
    if flag_new_file:
        if g_last_file_out:
            lg_dds.a("closing current tracking file due to rotation")
        file_out = f'{d}{str_iso_tg_tz_utc}#{v}_track.txt'
        lg_dds.a(f"started new tracking file {file_out}")
        g_last_file_out = file_out
    if dds_get_cfg_flag_download_test_mode():
        file_out = os.path.dirname(file_out) + '/' + \
                   TESTMODE_FILENAMEPREFIX + os.path.basename(file_out)

    # -----------------------------
    # write the tracking line alone
    # -----------------------------
    lat = '{:.6f}'.format(float(lat))
    lon = '{:.6f}'.format(float(lon))
    with open(file_out, 'a') as f:
        f.write(f"{str_iso_tg_tz_utc},{lat},{lon}\n")

    # ------------------------------
    # add info from LEF files, if so
    # ------------------------------

    ff_lef = glob.glob(f"{get_ddh_folder_path_lef()}/*.lef")
    for f_lef in ff_lef:
        with open(f_lef, 'r') as fl:
            j = fl.read()
            with open(file_out, 'a') as fo:
                fo.write(f"{str_iso_tg_tz_utc},{lat},{lon}***{j}\n")

        # delete the LEF file
        lg_log.a("deleting LEF file {}".format(f_lef))
        os.unlink(f_lef)
