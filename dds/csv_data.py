import bisect
import glob
import os.path
from utils.ddh_shared import dds_get_json_vessel_name, get_ddh_folder_path_dl_files


def _file_lowell_raw_csv_to_emolt_lt_csv(raw_csv_file):

    # CSV RAW data file: get start time and end time
    with open(raw_csv_file) as f:
        lr = f.readlines()
    stc = lr[1].split(',')[0].replace('.000', 'Z')
    etc = lr[-1].split(',')[0].replace('.000', 'Z')

    # track files: get file names involved
    v = dds_get_json_vessel_name().replace(" ", "_")
    fol = str(get_ddh_folder_path_dl_files())
    mask = "{}/{}T*Z#{}_track.txt"
    stf = glob.glob(mask.format(fol, stc.split('T')[0], v))
    etf = glob.glob(mask.format(fol, etc.split('T')[0], v))

    # track files: create big database
    dbt = []
    for i in stf:
        with open(i) as f:
            dbt += f.readlines()
    for i in etf:
        with open(i) as f:
            dbt += f.readlines()

    # OUT: new lowell file lt_*.csv
    raw_basename = os.path.basename(raw_csv_file)
    out_filename = 'lt_' + raw_basename
    out_file = raw_csv_file.replace(raw_basename, out_filename)
    with open(out_file, 'w') as f:
        # to each input raw line, add lat, lon from big database
        for ir in lr[1:]:
            t = ir.split(',')[0].replace('.000', 'Z')
            # database: get nearest index for this RAW time
            i = bisect.bisect_left(dbt, t) - 1
            i = i if i >= 0 else 0
            # database: get lat, lon for such index found
            _, lat, lon = dbt[i].split(',')
            ol = '{},{},{}'.format(ir.replace('\n', ''), lat, lon)
            f.write(ol)


def file_lowell_raw_csv_to_emolt_lt_csv(raw_csv_file):
    try:
        _file_lowell_raw_csv_to_emolt_lt_csv(raw_csv_file)
    except (Exception, ) as ex:
        print('ex', ex)