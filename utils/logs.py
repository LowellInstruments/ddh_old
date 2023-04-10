import datetime
from pathlib import Path
from dds.timecache import its_time_to
from utils.ddh_shared import (
    get_ddh_folder_path_logs,
    dds_get_json_vessel_name,
    get_ddh_folder_path_dl_files,
)
from mat.utils import PrintColors as PC


# experiment
g_tracking_path = ""


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
        return "{}/{}_{}.log".format(d, entity, now)

    def _retrieve_log_file_name(self):
        return self.f_name

    def are_enabled(self, b):
        self.enabled = b
        s = "{}_logs enabled = {}"
        self.a(s.format(self.label.upper(), self.enabled))

    # stands for 'print format'
    def _pf(self, s):
        if type(s) is bytes:
            s = s.decode()
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        s = "{} | [ {} ] {}".format(now, self.label.upper(), s)

        # color stuff, print() is called inside
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
    def a(self, s):
        if not self.enabled:
            return
        s = self._pf(s)
        with open(self.f_name, "a") as f:
            f.write(s + "\n")


lg_dds = DDSLogs("ble")
lg_aws = DDSLogs("aws")
lg_cnv = DDSLogs("cnv")
lg_sns = DDSLogs("sns")
lg_sqs = DDSLogs("sqs")
lg_gps = DDSLogs("gps")
lg_gui = DDSLogs("gui", entity="gui")
lg_net = DDSLogs("net")
lg_rbl = DDSLogs("rbl")
lg_emo = DDSLogs("emo")


# these NORMAL logs are local
def dds_log_core_start_at_boot():

    # create NORMAL log folder if it does not exist
    d = str(get_ddh_folder_path_logs())
    Path(d).mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    lg_dds.a("started normal logs on {}".format(ts))


# these TRACKING logs get uploaded
def dds_log_tracking_start_at_boot():

    v = dds_get_json_vessel_name().replace(" ", "_")
    d = str(get_ddh_folder_path_dl_files())

    # create TRACKING log folder if it does not exist
    d = "{}/ddh_{}/".format(d, v)
    Path(d).mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    lg_dds.a("started tracking logs on {}".format(ts))
    global g_tracking_path
    g_tracking_path = "{}/track_{}_{}.txt".format(d, v, ts)


def dds_log_tracking_add(lat, lon):

    assert g_tracking_path != ""

    if not lat:
        return

    # conditional, cache-based, GPS tracking log
    if not its_time_to("track_boat_gps", t=10):
        return

    # we don't want to use 'lg' functions here
    now = datetime.datetime.now().strftime("%m-%d-%y %H:%M:%S")
    s = "{} | {}\n".format(now, "{},{}".format(lat, lon))
    with open(g_tracking_path, "a") as f:
        f.write(s)
