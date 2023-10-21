import threading
import time

from rpc.rpc_rx import srv_cmd_fxn, srv_notify_fxn
from rpc.rpc_tx import cli_cmd_fxn, cli_notify_fxn


if __name__ == '__main__':
    th_sc = threading.Thread(target=srv_cmd_fxn)
    th_sc.start()
    th_cc = threading.Thread(target=cli_cmd_fxn)
    th_cc.start()

    time.sleep(2)
    th_sn = threading.Thread(target=srv_notify_fxn)
    th_sn.start()
    th_cn = threading.Thread(target=cli_notify_fxn)
    th_cn.start()
