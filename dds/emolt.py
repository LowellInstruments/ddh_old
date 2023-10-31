from collections import namedtuple

from mat.utils import linux_is_rpi
from utils.logs import lg_emo as lg
from utils.ddh_shared import dds_get_is_emolt_box_flag_file, dds_get_json_vessel_name
import pandas as pd
import os
from os.path import exists


GROUPED_S3_FILE_FLAG = '/home/pi/li/.ddt_this_box_has_grouped_s3_uplink.flag'

# ----------------------------------------------------------------------
# RAW CSV file -> emolt CSV file 'zt_*' -> header-less file %85 -> msg
# msg :message for Rockblocks to send
# ----------------------------------------------------------------------


COL_NAME_T = "Temperature (C)"
COL_NAME_D = "Depth (m)"


EmoltMsgShortHaul = namedtuple(
    "EmoltMsgShortHaul",
    "min_d_df_85 "
    "max_d_df_85 "
    "mean_d_df_85 "
    "std_d_df_85 "
    "min_t_df_85 "
    "max_t_df_85 "
    "mean_t_df_85 "
    "std_t_df_85",
)


def this_box_has_grouped_s3_uplink():
    return exists(GROUPED_S3_FILE_FLAG)


def ddh_is_emolt_box():
    return os.path.exists(dds_get_is_emolt_box_flag_file())


def ddh_is_dev_platform():
    return not linux_is_rpi()


def file_moana_raw_csv_to_emolt_csv(path, lat, lon):

    # RAW: file after the moana decode() function is called
    path = path.replace(".bin", ".csv")

    # RAW: file directly from converting .BIN file
    if "moana" not in path.lower():
        lg.a("error: {} is not a moana CSV file".format(path))
        return 1

    # get some useful fields from first line
    with open(path, "r") as f:
        ll = f.readlines()
        dl_datetime = ll[0].split(",")[1]
        dl_datetime = dl_datetime.replace("\n", "")
        dl_date, dl_time = dl_datetime.split(" ")
        day, mon, yyyy = dl_date.split("/")
        hh, mm, ss = dl_time.split(":")

    # ---------------------------------
    # build output filename 'zt...csv'
    # ---------------------------------
    vn = dds_get_json_vessel_name()
    vnum = os.getenv("DDH_BOX_SERIAL_NUMBER")
    lg_sn = os.path.basename(path).split("_")[1]
    ofn = "zt_" + lg_sn + "_" + yyyy + day + mon + "_"
    ofn += hh + mm + ss + "_" + vn + ".csv"
    ofn = ofn.replace("\n", "")
    ofn = "{}/{}".format(os.path.dirname(path), ofn)
    print("moana raw file name:", path)
    print("emolt csv file name:", ofn)

    # create header of output filename
    with open(ofn, "w") as fw:
        with open(path, "r") as fr:
            fw.write("Probe Type,Moana\n")
            fw.write("Serial Number,{}\n".format(lg_sn))
            fw.write("Vessel Number,{}\n".format(vnum))
            fw.write("Vessel Name,{}\r\n".format(vn))
            fw.write("Date Format,YYYY-MM-DD\n")
            fw.write("Time Format,HH24:MI:SS\n")
            fw.write("Temperature,C\n")
            fw.write("Depth,m\n")
            fw.write(
                "HEADING,datet(GMT),lat,lon,{},{}\n".format(COL_NAME_T, COL_NAME_D)
            )

            # lose the Moana RAW file header
            ll = fr.readlines()[10:]
            for i in ll:
                # i: '27/03/2023,15:47:06,4.4,22.516
                (
                    line_date,
                    line_time,
                    _dbar,
                    _temp,
                ) = i.split(",")
                if float(_dbar) < 0:
                    continue
                # line_out: DATA,2023-03-10 11:11:23,lat,lon,5.2,1.4
                lo = "{},{} {},{},{},{:.1f},{:.1f}\n"
                lo = lo.format(
                    "DATA", line_date, line_time, lat, lon, float(_temp), float(_dbar)
                )
                fw.write(lo)

    return ofn


def file_rn4020_raw_to_emolt_csv(path):
    # todo --> do this
    pass


def file_emolt_csv_to_hl(path, logger_type):
    path_hl = "{}.hl".format(path)
    print("emolt csv  file name:", path)
    print("headerless file name:", path_hl)

    if logger_type == "moana":
        with open(path_hl, "w") as fp:
            with open(path, "r") as fi:
                il = fi.readlines()
                # get rid of the Moana file header
                for i in il[8:]:
                    fp.write(i)

    elif logger_type == "rn4020":
        # todo ----> do this
        pass
    else:
        assert False

    return path_hl


def file_out_hl_process_xc_85(path) -> EmoltMsgShortHaul:

    lg.a("processing header-less file: {}".format(path))
    df = pd.read_csv(path)
    df_85 = df.loc[(df[COL_NAME_D] > 0.85 * max(df[COL_NAME_D]))]
    _d = df_85[COL_NAME_D]
    _t = df_85[COL_NAME_T]

    # fill variables
    min_d_df_85 = _d.min()
    max_d_df_85 = _d.max()
    mean_d_df_85 = _d.mean()
    std_d_df_85 = _d.std()
    min_t_df_85 = _t.min()
    max_t_df_85 = _t.max()
    mean_t_df_85 = _t.mean()
    std_t_df_85 = _t.std()

    # print summary
    print("\tmin_d_df_85  = {:.2f}".format(min_d_df_85))
    print("\tmax_d_df_85  = {:.2f}".format(max_d_df_85))
    print("\tmean_d_df_85 = {:.2f}".format(mean_d_df_85))
    print("\tstd_d_df_85  = {:.2f}".format(std_d_df_85))
    print("\tmin_t_df_85  = {:.2f}".format(min_t_df_85))
    print("\tmax_t_df_85  = {:.2f}".format(max_t_df_85))
    print("\tmean_t_df_85 = {:.2f}".format(mean_t_df_85))
    print("\tstd_t_df_85  = {:.2f}".format(std_t_df_85))
    print("\n\tDataframe percentile 85 = \n{}".format(df_85))

    # build a namedtuple
    m = EmoltMsgShortHaul(
        min_d_df_85,
        max_d_df_85,
        mean_d_df_85,
        std_d_df_85,
        min_t_df_85,
        max_t_df_85,
        mean_t_df_85,
        std_t_df_85,
    )

    if os.path.isfile(path):
        lg.a("deleting temporary header-less file: {}".format(path))
        os.unlink(path)

    return m


if __name__ == "__main__":
    MOANA_RAW_FILENAME = "{}/MOANA_0190_29.csv".format("/tmp")
    emolt_csv_file = file_moana_raw_csv_to_emolt_csv(
        MOANA_RAW_FILENAME, lat="4.444444", lon="5.555555"
    )
    hl_csv_file = file_emolt_csv_to_hl(emolt_csv_file, logger_type="moana")
    file_out_hl_process_xc_85(hl_csv_file)
