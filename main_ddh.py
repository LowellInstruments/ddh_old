import os
import signal
import sys
import time
from multiprocessing import Process
from PyQt5.QtWidgets import QApplication
from ddh.gui.main_gui import DDH, on_ctrl_c
from mat.linux import linux_app_write_pid_to_tmp, linux_is_process_running
from utils.ddh_shared import (
    PID_FILE_DDH,
    NAME_EXE_DDH_CONTROLLER,
    PID_FILE_DDH_CONTROLLER,
    NAME_EXE_DDH,
    ddh_get_gui_closed_flag_file, NAME_EXE_BRT, ddh_kill_by_pid_file,
)
import setproctitle
from utils.logs import lg_gui as lg
from utils.wdog import gui_dog_get
import subprocess as sp


def main_ddh():
    setproctitle.setproctitle(NAME_EXE_DDH)
    linux_app_write_pid_to_tmp(PID_FILE_DDH)

    assert sys.version_info >= (3, 9)
    signal.signal(signal.SIGINT, on_ctrl_c)

    app = QApplication(sys.argv)
    ex = DDH()
    ex.show()
    sys.exit(app.exec_())


def controller_main_ddh():

    # don't run if brt is running
    if linux_is_process_running(NAME_EXE_BRT):
        print('brt running, ddh should not')
        return

    s = NAME_EXE_DDH_CONTROLLER
    p = PID_FILE_DDH_CONTROLLER
    setproctitle.setproctitle(s)
    linux_app_write_pid_to_tmp(p)
    lg.a(f"=== {s} started ===")
    lg.a(f"=== {s} launches child ===")
    p = Process(target=main_ddh)
    p.start()

    # maybe left from before
    f = ddh_get_gui_closed_flag_file()
    if os.path.exists(f):
        os.unlink(f)

    while 1:
        time.sleep(5)
        v = gui_dog_get()
        kill = 0
        if os.path.exists(f):
            os.unlink(f)
            lg.a(f"=== debug: user closed {s} ===")
            kill = 1
        if v > 30 and time.perf_counter() > v + 30:
            # detects hangs of child GUI
            lg.a(f"=== {s} debug: {time.perf_counter()}, {v} child seems crashed ===")
            kill = 1
        if kill:
            # in this order or message does not show
            lg.a(f'debug: closing GUI, crontab will relaunch it', show_ts=0)
            # this kills everything DDH, not DDS
            ddh_kill_by_pid_file(only_child=False)


if __name__ == "__main__":

    # ------------------------
    # run DDH controller
    # ------------------------

    # debug: run without controller
    # main_ddh()
    # sys.exit(0)

    if not linux_is_process_running(NAME_EXE_DDH_CONTROLLER):
        controller_main_ddh()
    else:
        s = NAME_EXE_DDH_CONTROLLER
        print(f"not launching {s}, already running at python level")
