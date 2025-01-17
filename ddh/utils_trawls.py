import glob
import os.path
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
