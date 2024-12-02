#!/usr/bin/env python3
import multiprocessing
import threading
import time
import setproctitle
import subprocess as sp
import uvicorn
from fastapi import FastAPI
import requests
from utils.ddh_config import exp_get_use_smart_lock_out_time


# instead, DDN port is 9000 & 9001, other API port is 8000 & 80001
DDA_PORT = 8050
NAME_EXE_DDA = "main_dda"
MAX_TIME_DIFF = 5 * 60
app = FastAPI()
use = exp_get_use_smart_lock_out_time()
# g_d: global dictionary loggers last seen
g_d = {}


# debug
DEBUG = True
if DEBUG:
    use = 1
    MAX_TIME_DIFF = 3


def _get_now():
    return int(time.perf_counter())



def _p(s):
    print(f'    {s}')


@app.get('/add')
async def ep_add(mac):
    # used when just download a logger
    if use != 1:
        return
    global g_d
    t_n = _get_now()
    _p(f'add {mac} | {t_n}')
    g_d[mac] = t_n


@app.get('/del')
async def ep_del(mac):
    # used on button clear specific lock-out time
    if use != 1:
        return
    global g_d
    if mac in g_d.keys():
        _p(f'del {mac}')
        del g_d[mac]


@app.get('/del_all')
async def ep_del_all():
    # used on button clear all lock-out time
    if use != 1:
        return
    global g_d
    _p('del_all')
    g_d = {}


@app.get('/update')
async def ep_update(mac):
    # used when seen a logger in conjunction with get
    if use != 1:
        return
    global g_d
    if mac not in g_d.keys():
        return
    t_n = _get_now()
    _p(f'update {mac} | {t_n}')
    g_d[mac] = t_n


@app.get('/get')
async def ep_get(mac):
    # used when querying after mac_is_not_in_Black
    # used in conjunction with update
    if use != 1:
        return 0
    global g_d
    t_n = _get_now()
    if mac not in g_d.keys():
        _p(f'get {mac} not present')
        return 0

    t_o = g_d[mac]
    if t_n > t_o + MAX_TIME_DIFF:
        # present but expired
        s = (f'get {mac} | {t_o} -> expired, '
             f'{t_o} differs > {MAX_TIME_DIFF} from now {t_n}')
        _p(s)
        return 0

    # present and not expired
    _p(f'get {mac} | {t_o}')
    return 1


@app.get('/list')
async def ep_list(mac):
    if use != 1:
        return
    global g_d

    # enable this method only when debugging
    if not DEBUG:
        _p('list method NOT to be used on production')
        return

    t_n = _get_now()
    if g_d:
        _p(f'now {int(t_n)}, list:')
    else:
        _p(f'now {int(t_n)}, list: EMPTY')
    for mac, t_o in g_d.items():
        s = 'v' if t_n <= t_o + MAX_TIME_DIFF else 'x'
        _p(f'    [ {s} ] {mac} | {t_o}')
    return g_d


def main_dda_as_th():
    th = threading.Thread(target=main_dda)
    th.start()


def main_dda():
    # remove any failed previous runs
    killall_main_dda()
    def _main_dda():
        setproctitle.setproctitle(NAME_EXE_DDA)
        uvicorn.run(app, host="0.0.0.0", port=DDA_PORT)
    p = multiprocessing.Process(target=_main_dda)
    p.start()


def killall_main_dda():
    c = f'killall {NAME_EXE_DDA}'
    sp.run(c, shell=True)


def dda_op(ep, mac):
    assert ep in ('add', 'get', 'update', 'del', 'list')
    u = f'http://0.0.0.0:{DDA_PORT}/{ep}?mac={mac}'
    try:
        return requests.get(u, timeout=1)
    except (Exception, ) as ex:
        _p(f'error: dda_op -> {ex}')


if __name__ == "__main__":

    # test, no api running
    dda_op('del', '')

    if not DEBUG:
        # example, when called from DDH
        main_dda()
    else:
        _p('calling main_dda_as_thread')
        main_dda_as_th()
        _m = "11"
        time.sleep(1)

        # add value
        dda_op('add', _m)
        _p('sleep 1')
        time.sleep(1)
        _p(f'now is {_get_now()}')

        # query, it is there, and update
        rv = dda_op('get', _m)
        if rv:
            dda_op('update', _m)
        else:
            dda_op('del', _m)
        _p('sleep 1')
        time.sleep(1)
        _p(f'now is {_get_now()}')

        # list present ones
        rv = dda_op('list', '')
        _p(f'list {rv.text}')

        # query after too much time, will not update
        _p(f'sleep {MAX_TIME_DIFF + 1}')
        time.sleep(MAX_TIME_DIFF + 1)
        _p(f'now is {_get_now()}')
        rv = dda_op('get', _m)
        if int(rv.text):
            dda_op('update', _m)
        else:
            dda_op('del', _m)
        rv = dda_op('list', '')
        _p(f'list {rv.text}')
