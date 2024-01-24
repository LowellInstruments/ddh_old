import bisect
import glob
import os.path

from utils.ddh_config import dds_get_cfg_vessel_name
from utils.ddh_shared import get_ddh_folder_path_dl_files
from utils.logs import lg_cnv as lg


# outputs a CST file (CSV file + tracking GPS info)
def _file_lowell_raw_csv_to_emolt_lt_csv(filename):

    # correct a bad input parameter filename
    csv_f = filename.replace('.lix', '_TAP.csv')

    # read csv file into lines
    lg.a(f'generating trawling for input file {csv_f}')
    with open(csv_f) as f:
        csv_ll = f.readlines()

    # use first and last csv lines to know names of GPS track files involved
    stc = csv_ll[1].split(',')[0].replace('.000', 'Z')
    etc = csv_ll[-1].split(',')[0].replace('.000', 'Z')
    v = dds_get_cfg_vessel_name().replace(" ", "_")
    fol = str(get_ddh_folder_path_dl_files())
    mask = "{}/ddh#{}/{}T*Z#{}_track.txt"
    # mask: dl_files/ddh#<v>/2023-12-12T*Z#<v>_track.txt
    mask_stf = mask.format(fol, v, stc.split('T')[0], v)
    mask_etf = mask.format(fol, v, etc.split('T')[0], v)
    stf = glob.glob(mask_stf)
    etf = glob.glob(mask_etf)

    # filter by unique tracking file names
    utf = list(set(stf).union(set(etf)))
    if not utf:
        lg.a(f'error: no track files found for mask {mask}')
        return

    # track files: create big database of lines
    tf_ll = []
    for i in utf:
        with open(i) as f:
            tf_ll += f.readlines()

    # ------------------------------------------------
    # write new output file lt_*.cst (csv + tracking)
    # ------------------------------------------------
    bn = os.path.basename(csv_f)
    cst_filename = os.path.dirname(csv_f) + '/lt_' + bn[:-4] + '.cst'

    with open(cst_filename, 'w') as f:

        # cst has 2 more columns in the headers
        hh = csv_ll[0].replace('\n', '') + ',lat,lon\n'
        f.write(hh)

        # get each input CSV line (il)
        for il in csv_ll[1:]:

            # convert (il) time to tracking file time format (tf_t)
            tf_t = il.split(',')[0].replace('.000', 'Z')

            # use (tf_t) to get most significant tracking line index (i)
            i = bisect.bisect_left(tf_ll, tf_t) - 1
            i = i if i >= 0 else 0

            # get rid of any LEF marker in the indexed tracking line
            # x: 2023-12-15T18:56:40Z,38.000000,-83.000000***LEF info
            x = tf_ll[i].split('***')[0]
            x += "" if x.endswith('\n') else '\n'
            _, lat, lon = x.split(',')

            # output line (ol) is input line + lat, lon from tracking line
            ol = '{},{},{}'.format(il.replace('\n', ''), lat, lon)
            f.write(ol)

    lg.a(f'OK: generated trawling CST file {cst_filename}')


def file_lowell_raw_csv_to_emolt_lt_csv(filename):
    try:
        _file_lowell_raw_csv_to_emolt_lt_csv(filename)
    except (Exception, ) as ex:
        lg.a(f'error: file_lowell_raw_csv_to_emolt_lt_csv: {ex}')


if __name__ == '__main__':
    ft = 'dl_files/d0-2e-ab-d9-29-48/9999999_BIL_20231201_142920_TAP.csv'
    file_lowell_raw_csv_to_emolt_lt_csv(ft)
