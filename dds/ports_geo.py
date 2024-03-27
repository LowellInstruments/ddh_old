import time

import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import pyproj

from dds.timecache import its_time_to
from utils.ddh_shared import ddh_get_folder_path_in_port_db
from utils.logs import lg_gps as lg


g_ports = None
g_ports_loaded = False
PATH_SHP_FILE = f'{ddh_get_folder_path_in_port_db()}/emolt_ports.shp'


def ddh_load_fishing_ports_db():

    global g_ports
    global g_ports_loaded
    try:
        el = time.perf_counter()
        # read in file with data
        g_ports = gpd.read_file(PATH_SHP_FILE)
        # use same reference for both points and the ports
        g_ports.crs = pyproj.CRS("+proj=longlat +datum=WGS84 +no_defs")
        el = int(el - time.perf_counter())
        lg.a(f'OK: loaded ports database in {el} seconds')
        g_ports_loaded = True
    except (Exception, ) as ex:
        lg.a(f'error: load ports database -> {str(ex)}')
        g_ports_loaded = False


def ddh_is_in_port(lat, lon, dl=False):

    global g_ports_loaded
    if not g_ports_loaded:
        print(f'error: ddh_is_in_port -> no database')
        return

    # benchmark
    el = time.perf_counter()

    # create dataframe containing point of interest
    df = pd.DataFrame({
        'LATITUDE': pd.Series(dtype='float'),
        'LONGITUDE': pd.Series(dtype='float')
    })
    df.loc[1] = [lat, lon]

    # convert df to geo_df
    geo_df = gpd.GeoDataFrame(df,
                              geometry=[Point(xy) for xy in zip(df["LONGITUDE"], df["LATITUDE"])])

    # use same reference for both points and the ports
    geo_df.crs = pyproj.CRS("+proj=longlat +datum=WGS84 +no_defs")

    # get vector of NaN (not in port) or Port Names (in port)
    global g_ports
    res_ports = geo_df.sjoin(g_ports,
                             how="left", predicate="intersects")['PORT_NAME']

    # res_ports: panda series, True means out of port
    out_port = list(res_ports.isna())[0]
    in_port = not out_port

    # benchmark
    el = int(el - time.perf_counter())
    lg.a(f'debug: in_port check = {in_port}, took {el} seconds')

    if dl and in_port and its_time_to('tell_its_in_port', 600):
        lg.a(f'warning: not downloading, DDH is in port')

    return in_port


if __name__ == '__main__':
    # no port
    print('in_port', ddh_is_in_port(35, -75))
    # new bedford port
    print('in_port_nb', ddh_is_in_port(41.63, -70.91))
