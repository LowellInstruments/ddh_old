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


def main_test_ver():
    import subprocess as sp
    s = '.ddh_version'
    # get local version
    with open(s, 'r') as f:
        vl = f.readline().replace('\n', '')

    # get github version
    c = f'wget https://raw.githubusercontent.com/LowellInstruments/ddh/master/{s}'
    c += f' -O /tmp/{s}'
    rv = sp.run(c, shell=True, stdout=sp.PIPE, stderr=sp.PIPE)
    if rv.returncode == 0:
        with open(f'/tmp/{s}', 'r') as f:
            vg = f.readline().replace('\n', '')

    if vl < vg:
        print('needs update')


# test
if __name__ == '__main__':
    main_test_aws()
