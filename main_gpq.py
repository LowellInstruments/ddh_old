#!/usr/bin/env python3

import setproctitle
from fastapi import FastAPI
from datetime import datetime

from api.api_utils import (
                           linux_app_write_pid_to_tmp,
                           CTT_API_OK)
import uvicorn

from dds.gpq import GpqW, NGpqR, FMT_RECORD

# instead, the DDN port is 9000
DDH_PORT_API = 8000
NAME_EXE_API = "main_api"
PID_FILE_API = "/tmp/{}.pid".format(NAME_EXE_API)


app = FastAPI()
FMT_RECORD_GPQ_DB = '%Y/%m/%d %H:%M:%S'
FMT_FILENAME = '%y%m%d%H.json'
FMT_API_GPQ = '%Y%m%d%H%M%S'


# global vars
g_w = GpqW()
g_r = NGpqR()


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
async def ep_gpq(dt_api, delta_mm):
    # delta_mm: max minutes of difference
    # http://0.0.0.0:8000/gpq?dt_api=20240102030405&delta_mm=30
    dn = datetime.strptime(dt_api, FMT_API_GPQ)
    dt_s = dn.strftime(FMT_RECORD)
    rv = g_r.query(dt_s, delta_mm)
    d = {
        "gpq_get": CTT_API_OK,
        'rv': f'{rv[0], rv[1]}'
    }
    return d



def main_api():
    # docs at http://0.0.0.0/port/docs
    setproctitle.setproctitle(NAME_EXE_API)
    linux_app_write_pid_to_tmp(PID_FILE_API)
    uvicorn.run(app, host="0.0.0.0", port=DDH_PORT_API)


if __name__ == "__main__":
    main_api()
