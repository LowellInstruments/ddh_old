import os
from dds.aws import _aws_s3_sync_process
from dds.rbl import _rbl_send, rbl_decode


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
    sn = os.getenv("DDH_BOX_SERIAL_NUMBER") or "1234567"
    m_lg_sn = "{:08x}".format(int(sn))
    print(m_lg_sn)


if __name__ == '__main__':
    # main_test_aws()
    main_test_rbl()
    pass
