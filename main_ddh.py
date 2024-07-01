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
    ddh_get_gui_closed_flag_file, NAME_EXE_BRT,
)
import setproctitle
from utils.logs import lg_gui as lg


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
    lg.a("=== {} started ===".format(s))

    while 1:
        lg.a("=== {} launches child ===".format(s))
        p = Process(target=main_ddh)
        p.start()
        p.join()
        lg.a("=== {} waits child ===".format(s))
        p = ddh_get_gui_closed_flag_file()
        if os.path.exists(p):
            lg.a("=== debug: user closed ===")
            os.unlink(p)
            break

        # only triggers upon exceptions
        time.sleep(5)

    lg.a("=== {} ended ===".format(s))


if __name__ == "__main__":

    # ------------------------
    # run DDH controller
    # ------------------------

    if not linux_is_process_running(NAME_EXE_DDH_CONTROLLER):
        controller_main_ddh()
    else:
        e = "not launching {}, already running at python level"
        print(e.format(NAME_EXE_DDH_CONTROLLER))
