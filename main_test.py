import datetime
import os

from ddh.db.db_his import *
from dds.aws import _aws_s3_sync_process
from dds.rbl import _rbl_send, rbl_decode
from utils.ddh_shared import ddh_get_db_history_file


# ----------------------------------------------
# this file allows testing snippets of code in
# pycharm without having to take care of paths
# ----------------------------------------------

def main_test_aws():
    path = 'dl_files'
    if not os.path.isdir(path):
        os.mkdir(path)
    _aws_s3_sync_process()


def main_test_rbl():
    # _rbl_send(b'\x11\x22', fmt='bin')
    sn = os.getenv("DDH_BOX_SERIAL_NUMBER") or "123456f"
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
def main_test_db_his():
    db = DBHis(ddh_get_db_history_file())
    db.delete_all()
    now = datetime.datetime.now()
    later = now + datetime.timedelta(minutes=10)
    db.add("12:34", 12345, "ok", "1.111111", "2.222222", later)
    db.add("55:55", 55555, "ok", "3.333333", "4.444444", now)
    db.add("55:55", 55555, "error", "5.555555", "6.666666", now)
    for r in db.get_all(400):
        t = r["sws_time"]
        print(datetime.datetime.fromtimestamp(t))


if __name__ == '__main__':
    main_test_db_his()
