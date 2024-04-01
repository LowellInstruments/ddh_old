import datetime
import glob
import os
import requests
from PyQt5.QtGui import QMovie
from mat.utils import linux_is_rpi
from utils.ddh_shared import (
    ddh_get_folder_path_res,
)
from utils.logs import lg_gui as lg


def gui_populate_maps_tab(my_app):
    addr_ddn_api = 'ddn.lowellinstruments.com'
    port_ddn_api = 9000
    deg = 'F'
    fr = str(ddh_get_folder_path_res())
    d = str(datetime.datetime.now().strftime('%Y%m%d'))
    fe = f"{fr}/error_maps.gif"
    fg = f"{fr}/{d}_{deg}.gif"
    fl = fg

    # delete tdm gifs which are not the current one
    ls = glob.glob(f"{fr}/*.gif")
    for fi in ls:
        if fi == fl:
            continue
        lg.a(f'deleting old tdm file {fi}')
        os.unlink(fi)

    # when developing, force re-download
    if not linux_is_rpi() and os.path.exists(fg):
        lg.a(f'we developing, deleting tdm file {fg}')
        os.unlink(fg)

    #  we don't have today's file, download gif from server
    if not os.path.exists(fg):
        lg.a(f"debug: requesting today's tdm file {fg}")
        t = 5
        url = f'http://{addr_ddn_api}:{port_ddn_api}/dtm?t={d}&deg={deg}'
        try:
            rsp = requests.get(url, timeout=t)
            rsp.raise_for_status()
            # save gif to local file system
            with open(fg, 'wb') as f:
                f.write(rsp.content)
                fl = fg
        except (Exception,) as err:
            lg.a(f'error: maps request -> {err}')
            fl = fe
    else:
        lg.a(f"debug: re-using today's tdm file {fg}")

    # load the map
    a = my_app
    a.gif_map = QMovie(fl)
    a.lbl_map.setMovie(a.gif_map)
    a.gif_map.start()