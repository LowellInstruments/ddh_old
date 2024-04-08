#!/usr/bin/env python3
import threading
import time

import requests
import setproctitle
from fastapi import FastAPI
from datetime import datetime

from requests import HTTPError

from api.api_utils import (
                           linux_app_write_pid_to_tmp,
                           CTT_API_OK)
import uvicorn

from dds.gpq import GpqW, FMT_RECORD, GpqR

# instead, the DDN port is 9000
DDH_PORT_GPQ = 8001
NAME_EXE_GPQ = "main_gpq"
PID_FILE_GPQ = "/tmp/{}.pid".format(NAME_EXE_GPQ)


app = FastAPI()
FMT_RECORD_GPQ_DB = '%Y/%m/%d %H:%M:%S'
FMT_FILENAME = '%y%m%d%H.json'
FMT_API_GPQ = '%Y%m%d%H%M%S'


# global vars
g_w = GpqW()
g_r = GpqR()


@app.put('/gpq')
async def ep_gpq(dt_api, lat, lon):
    # http://0.0.0.0:8000/gpq?dt_api=20240102030405&lat=lat1&lon=lon1
    dn = datetime.strptime(dt_api, FMT_API_GPQ)
    g_w.add(dn, lat, lon)
    d = {
        "gpq_put": CTT_API_OK,
        "dn": str(dn)
    }
    return d


@app.get('/gpq')
async def ep_gpq(dt_api):
    # delta_mm: max minutes of difference
    # http://0.0.0.0:8000/gpq?dt_api=20240102030405
    dn = datetime.strptime(dt_api, FMT_API_GPQ)
    dt_s = dn.strftime(FMT_RECORD)
    rv = g_r.query(dt_s)
    d = {
        "gpq_get": CTT_API_OK,
        'rv': f'{rv[0], rv[1], rv[2]}'
    }
    return d


def gpq_server():
    # docs at http://0.0.0.0/port/docs
    setproctitle.setproctitle(NAME_EXE_GPQ)
    linux_app_write_pid_to_tmp(PID_FILE_GPQ)
    uvicorn.run(app, host="0.0.0.0", port=DDH_PORT_GPQ)


def gpq_client():
    def req_get(u, time_out=1):
        try:
            _rsp = requests.get(u, timeout=time_out)
            _rsp.raise_for_status()
            return _rsp
        except (HTTPError, Exception,) as ex:
            print(f'req_get error -> {ex}')

    def req_put(u, time_out=1):
        try:
            _rsp = requests.put(u, timeout=time_out)
            _rsp.raise_for_status()
            return _rsp
        except (HTTPError, Exception,) as ex:
            print(f'req_put error -> {ex}')

    # wait api to boot
    time.sleep(.5)

    # client test
    u_put = (f'http://0.0.0.0:{DDH_PORT_GPQ}/gpq?'
             f'dt_api=20240102030405&'
             f'lat=lat1&lon=lon1')
    print('<- CLI put')
    rsp_put = req_put(u_put)
    print('-> CLI rsp_put', rsp_put.content)

    # client get
    u_get = (f'http://0.0.0.0:{DDH_PORT_GPQ}/gpq?'
             f'dt_api=20240102030410''')
    print('<- CLI get')
    rsp_get = req_get(u_get)
    print('-> CLI rsp_get', rsp_get.content)


if __name__ == "__main__":
    th = threading.Thread(target=gpq_client)
    th.start()
    gpq_server()
