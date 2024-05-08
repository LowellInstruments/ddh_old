import datetime
import glob
from ddh.db.db_his import *
from utils.ddh_config import dds_get_cfg_box_sn
from utils.ddh_shared import ddh_get_db_history_file, get_ddh_folder_path_dl_files


# ----------------------------------------------
# this file allows testing snippets of code in
# pycharm without having to take care of paths
# ----------------------------------------------

def main_test_aws():
    # path = 'dl_files'
    # if not os.path.isdir(path):
    #     os.mkdir(path)
    # _aws_s3_sync_process()

    # count number of files
    fol = str(get_ddh_folder_path_dl_files())
    ls = []
    for i in ('lid', 'lix', 'csv', 'cst', 'gps', 'bin'):
        ls += glob.glob(f'{fol}/**/*.{i}')
    print(ls)
    print(len(ls))


def main_test_rbl():
    # _rbl_send(b'\x11\x22', fmt='bin')
    sn = dds_get_cfg_box_sn() or "123456f"
    m_lg_sn = "{:08x}".format(int(sn, 16))
    print(m_lg_sn)


# test
if __name__ == '__main__':
    main_test_aws()
