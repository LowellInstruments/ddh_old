import datetime
import glob
import math
import os.path
import pandas as pd
import folium
import requests
from mat.utils import linux_is_rpi
from utils.ddh_config import dds_get_cfg_logger_mac_from_sn
from utils.ddh_shared import (
    get_dl_folder_path_from_mac,
    DDN_API_IP,
    DDN_API_PORT
)


g_db = {
    # fol: (files, current_index)
}


def _create_map_of_trawl(file_cst):

    file_html = file_cst.replace('.cst', '_trawl_map.html')

    # faster execution
    if os.path.exists(file_html):
        print(f'reusing file_html {file_html}')
        return file_html

    # load all data from CST file
    df = pd.read_csv(file_cst)
    ls_lat = df['lat']

    # check we can plot something
    _ = ls_lat.dropna()
    if _.empty:
        return

    # drop duplicates
    df = df.drop_duplicates('lat')
    ls_lat = df['lat']
    ls_lon = df['lon']
    ls_time = df['ISO 8601 Time']
    met = 'Dissolved Oxygen (mg/l)'
    lt = 'DO'
    if met not in df.columns:
        met = 'Pressure (dbar)'
        lt = 'TDO'
    units = met.split('(')[1].split(')')[0]
    ls_v = df[met]
    n = len(ls_lat)

    # parse map title 2402774_BIL_20241025_185306_TDO.cst
    bn = os.path.basename(file_cst)
    sn = bn.split('_')[0]
    year = bn.split('_')[2][:4]
    month = bn.split('_')[2][4:6]
    day = bn.split('_')[2][6:8]
    hh = bn.split('_')[3][:2]
    mm = bn.split('_')[3][2:4]
    wday = datetime.datetime(2017, 10, 20)
    wday = wday.strftime('%A')
    bn = f'{lt} logger {sn} deployed on '\
         f'{wday} {year}-{month}-{day} at {hh}:{mm}, ' \
         f'{n} samples'
    title_html = '''
         <head><style> html { overflow-y: hidden; } </style></head>
         <h3 align="center" style="font-size:16px"><b>''' + bn + '''</b></h3>'''


    # create the map
    origin_lat = ls_lat[0]
    origin_lon = ls_lon[0]
    m = folium.Map(
        location=[origin_lat, origin_lon],
        # max 18, very close
        # 10, shows ok 2 positions separated by .1
        zoom_start=10,
        )

    # add the title
    m.get_root().html.add_child(folium.Element(title_html))

    # add the markers
    for i, v in enumerate(ls_lat):
        # skips rows with no values
        if math.isnan(v):
            continue

        # place the marker
        s = f"""<table bgcolor="green">
            <tbody>
            <tr><td>{ls_time[i][:10]}</td></tr>
            <tr><td>{ls_time[i][11:19]}</td></tr>
            <tr><td>{ls_lat[i]}, {ls_lon[i]}</td></tr>
            <tr><td>{ls_v[i]} {units    }</td></tr>
            </tbody>
            </table>"""

        folium.Marker(
            location=[ls_lat[i], ls_lon[i]],
            popup=folium.Popup(s, max_width=100),
            tooltip=s
        ).add_to(m)

    # create the html output file
    m.save(file_html)
    return file_html


def try_create_map_of_trawl(file_cst):
    try:
        return _create_map_of_trawl(file_cst)
    except (Exception, ) as ex:
        print(f'error try_create_map_of_trawl -> {ex}')


def try_get_map_of_trawl(file_cst):
    h = file_cst.replace('.cst', 'trawl_map.html')
    if os.path.exists(h):
        return h
    print(f"requesting trawl map html file {os.path.basename(h)}")
    t = 5
    addr_ddn_api = DDN_API_IP if linux_is_rpi() else 'localhost'
    port_ddn_api = DDN_API_PORT
    url = f'http://{addr_ddn_api}:{port_ddn_api}/ddh_get_trawl_map?cst_filename={file_cst}'
    try:
        rsp = requests.get(url, timeout=t)
        rsp.raise_for_status()
        with open(h, 'wb') as f:
            f.write(rsp.content)
            print('OK: got trawl map file')
            return h
    except (Exception,) as err:
        print(f'error: try_get_map_of_trawl request -> {err}')


def get_last_trawl_of_a_logger(sn):
    mac = dds_get_cfg_logger_mac_from_sn(sn)
    fol = get_dl_folder_path_from_mac(mac)
    global g_db
    mask_cst = f'{fol}/*.cst'
    ls_cst = sorted(glob.glob(mask_cst))
    # update back the database with new content and index
    g_db[fol] = [ls_cst, -1]
    ls = g_db[fol][0]
    if ls:
        print(f'last cst file {ls[-1]}')
        return ls[-1]


def get_prev_trawl_of_a_logger(sn):
    global g_db
    mac = dds_get_cfg_logger_mac_from_sn(sn)
    fol = get_dl_folder_path_from_mac(mac)
    if fol not in g_db.keys():
        return
    ls, i = g_db[fol]
    if not ls:
        return
    i = (i - 1) % len(ls)
    prev_file = g_db[fol][0][i]
    # update back the database with new index
    g_db[fol] = [ls, i]
    return prev_file
