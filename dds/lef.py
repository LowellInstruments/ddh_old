import glob
import json
from settings import ctx
from utils.ddh_shared import get_ddh_folder_path_lef
import os


# ------------------------------------------------------
# LEF: lowell event file
# produced by module SQS, consumed by module utils/LOGS
# ------------------------------------------------------


def dds_create_folder_lef():
    r = get_ddh_folder_path_lef()
    os.makedirs(r, exist_ok=True)


def dds_create_file_lef(now, d):
    if not ctx.lef_en:
        return
    fol = str(get_ddh_folder_path_lef())
    path = "{}/{}.lef".format(fol, now)
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
