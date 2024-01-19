import glob
import json

from utils.ddh_config import dds_get_cfg_vessel_name
from utils.ddh_shared import get_ddh_folder_path_lef
import os


# ----------------------------------------------------------
# LEF: lowell event file
# upon a BLE download, a .LEF file is created
# the UTILS/LOGS module finds it, reads it and cats its
# content in current 'track_*.gps' file w/ a '***' marker
# ----------------------------------------------------------


def dds_create_folder_lef():
    r = get_ddh_folder_path_lef()
    os.makedirs(r, exist_ok=True)


def dds_create_file_lef(g, name):
    lat, lon, tg, speed = g
    d = {
        "dl_lat": lat,
        "dl_lon": lon,
        "dl_utc_tg": str(tg),
        "dl_speed": speed,
        "dl_filename": name,
        "dl_vessel": dds_get_cfg_vessel_name()
    }
    fol = str(get_ddh_folder_path_lef())
    path = "{}/dl_{}.lef".format(fol, name)
    with open(path, "w") as fl:
        # from dict to file
        json.dump(d, fl)


if __name__ == '__main__':
    # -----------------------------------------
    # how to grab json fields from track files
    # -----------------------------------------
    os.chdir("../dl_files/ddh#joaquim")
    s = glob.glob('*.txt')[-1]
    print('parsing track file', s)
    with open(s, 'r') as f:
        ll = f.readlines()
    for each_line in ll:
        if "***" in each_line:
            # from string to dict
            j = json.loads(each_line.split('***')[1])
            print(j['reason'])
