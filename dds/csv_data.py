import bisect
import glob
import os.path
from utils.ddh_shared import dds_get_json_vessel_name, get_ddh_folder_path_dl_files
from utils.logs import lg_cnv as lg


def _file_lowell_raw_csv_to_emolt_lt_csv(filename):

    # be sure of extensions
    raw_csv_file = filename
    if raw_csv_file.endswith('.lix'):
        raw_csv_file = filename[:-4] + '_TAP.csv'

    # CSV RAW data file: get start time and end time
    lg.a(f'generating trawling for input file {raw_csv_file}')
    with open(raw_csv_file) as f:
        lr = f.readlines()
    stc = lr[1].split(',')[0].replace('.000', 'Z')
    etc = lr[-1].split(',')[0].replace('.000', 'Z')

    # track files: get file names involved
    v = dds_get_json_vessel_name().replace(" ", "_")
    fol = str(get_ddh_folder_path_dl_files())
    mask = "{}/ddh#{}/{}T*Z#{}_track.txt"
    mask_stf = mask.format(fol, v, stc.split('T')[0], v)
    mask_etf = mask.format(fol, v, etc.split('T')[0], v)
    stf = glob.glob(mask_stf)
    etf = glob.glob(mask_etf)

    # keep only unique file names
    atf = list(set(stf).union(set(etf)))
    if not atf:
        lg.a(f'error: no track files found for mask {mask}')
        return

    # track files: create big database
    dbt = []
    for i in atf:
        with open(i) as f:
            dbt += f.readlines()

    # OUT: new lowell file lt_*.cst
    raw_basename = os.path.basename(raw_csv_file)
    out_filename = 'lt_' + raw_basename
    out_file = raw_csv_file.replace(raw_basename, out_filename)
    out_file = out_file[:-4] + '.cst'
    with open(out_file, 'w') as f:
        # headers first
        hh = lr[0].replace('\n', '') + ',lat,lon\n'
        f.write(hh)
        # to each input raw line, add lat, lon from big database
        for ir in lr[1:]:
            t = ir.split(',')[0].replace('.000', 'Z')
            # database: get nearest index for this RAW time
            i = bisect.bisect_left(dbt, t) - 1
            i = i if i >= 0 else 0
            # get rid of any LEF marker
            x = dbt[i].split('***')[0]
            # database: get lat, lon for such index found
            _, lat, lon = x.split(',')
            ol = '{},{},{}'.format(ir.replace('\n', ''), lat, lon)
            f.write(ol)
    lg.a(f'OK: generated trawling output file {out_filename}')


def file_lowell_raw_csv_to_emolt_lt_csv(filename):
    try:
        _file_lowell_raw_csv_to_emolt_lt_csv(filename)
    except (Exception, ) as ex:
        lg.a(f'error: file_lowell_raw_csv_to_emolt_lt_csv: {ex}')


if __name__ == '__main__':
    ft = 'dl_files/d0-2e-ab-d9-29-48/9999999_BIL_20231201_142920_TAP.csv'
    file_lowell_raw_csv_to_emolt_lt_csv(ft)
