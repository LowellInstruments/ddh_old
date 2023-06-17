import os
from dds.aws import _aws_s3_sync_process


# ----------------------------------------------
# this file allows testing snippets of code in
# pycharm without having to take care of paths
# ----------------------------------------------

def main_test_aws():
    path = 'dl_files'
    if not os.path.isdir(path):
        os.mkdir(path)
    _aws_s3_sync_process()


if __name__ == '__main__':
    main_test_aws()
