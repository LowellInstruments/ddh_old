#!/usr/bin/env python3
import multiprocessing
import threading
import time
import setproctitle
import uvicorn
from fastapi import FastAPI
import requests
from utils.ddh_config import exp_get_use_smart_lock_out_time


# instead, DDN port is 9000 & 9001, other API port is 8000 & 80001
DDA_PORT = 8050
NAME_EXE_DDA = "main_dda"
MAX_TIME_ELAPSED = 5 * 60
app = FastAPI()
use = exp_get_use_smart_lock_out_time()
# g_d: global dictionary loggers last seen
g_d = {}


# debug
DEBUG = True
if DEBUG:
    use = 1
    MAX_TIME_ELAPSED = 3



def _p(s):
    print(s)


@app.get('/add')
async def ep_add(mac, forced):
    # use cases:
    #    - just download a logger, forced is 1
    #    - seen a logger
    if use != 1:
        return
    global g_d
    t_now = time.perf_counter()

    # fresh new
    if forced:
        g_d[mac] = t_now
        print(f'add {mac}')
        return

    # not expired, update
    t_old = g_d[mac]
    if mac in g_d.keys():
        if t_now <= t_old + MAX_TIME_ELAPSED:
            g_d[mac] = t_now
            _p(f'update {mac}')


@app.get('/del')
async def ep_del(mac):
    if use != 1:
        return
    global g_d

    if mac in g_d.keys():
        _p(f'del {mac}')
        del g_d[mac]


@app.get('/del_all')
async def ep_del_all():
    if use != 1:
        return
    global g_d

    _p('del_all')
    g_d = {}


@app.get('/get')
async def ep_get(mac):
    if use != 1:
        return
    global g_d
    t_now = time.perf_counter()

    # not even in dictionary
    if mac not in g_d.keys():
        _p(f'get {mac} not present')
        return 0

    # not expired
    t_old = g_d[mac]
    if t_now <= t_old + MAX_TIME_ELAPSED:
        g_d[mac] = t_now
        _p(f'get {mac} present')
        return 1

    # expired
    del g_d[mac]
    _p(f'get {mac} present but expired, delete')
    return 0


@app.get('/list')
async def ep_list():
    if use != 1:
        return
    global g_d

    # use this method only when debugging
    if not DEBUG:
        _p('list method NOT to be used on production')
        return

    if not g_d:
        _p('list is empty')
        return {}

    _p('list:')
    t_now = time.perf_counter()
    for mac, t_old in g_d.items():
        s = 'v' if t_now <= t_old + MAX_TIME_ELAPSED else 'x'
        _p(f'  [ {s} ] {mac}')
    return g_d


def main_dda_as_th():
    th = threading.Thread(target=main_dda)
    th.start()


def main_dda():
    def _main_dda():
        setproctitle.setproctitle(NAME_EXE_DDA)
        uvicorn.run(app, host="0.0.0.0", port=DDA_PORT)
    p = multiprocessing.Process(target=_main_dda)
    p.start()


if __name__ == "__main__":
    if not DEBUG:
        # example, when called from DDH
        main_dda()
    else:
        _p('calling main_dda_as_thread')
        main_dda_as_th()
        # test
        time.sleep(1)
        u = f'http://0.0.0.0:{DDA_PORT}'
        rv = requests.get(f'{u}/list')
        requests.get(f'{u}/add?mac=11&forced=1')
        rv = requests.get(f'{u}/list')
        print('rv list', rv.text)
        time.sleep(MAX_TIME_ELAPSED + 1)
        rv = requests.get(f'{u}/list')
        print('rv list', rv.text)
