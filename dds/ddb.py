#!/usr/bin/env python3
import multiprocessing
import sys
import time
from multiprocessing import Process
import setproctitle
from ddh.utils_graph import utils_graph_tdo_classify_files_fast_mode
from dds.timecache import its_time_to
from mat.linux import linux_is_process_running
from utils.logs import lg_gra as lg


DDB_PROC_NAME = "dds_ddb"


def _ddb_serve():
    setproctitle.setproctitle(DDB_PROC_NAME)
    utils_graph_tdo_classify_files_fast_mode()
    # instead of return prevents zombie processes
    sys.exit(0)


def ddb_serve():
    # useful to remove past DDB zombie processes
    multiprocessing.active_children()
    if linux_is_process_running(DDB_PROC_NAME):
        lg.a(f"error: seems last {DDB_PROC_NAME} took a long time")
    else:
        s = f'launching {DDB_PROC_NAME}'
        if its_time_to(s, 600):
            lg.a('_' * len(s))
            lg.a(s)
            lg.a('_' * len(s))
            p = Process(target=_ddb_serve)
            p.start()


# test
if __name__ == '__main__':
    ddb_serve()
