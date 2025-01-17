import glob
import json
import os
from utils.ddh_shared import (
    get_ddh_folder_path_dl_files
)


PATH_AWS_CP_DB = f'{get_ddh_folder_path_dl_files()}/.aws_cp.db'


def _inventory_load_from_file():
    with open(PATH_AWS_CP_DB) as f:
        return json.loads(f.read())


def _inventory_save_to_file(db: dict):
    with open(PATH_AWS_CP_DB, 'w') as f:
        f.write(json.dumps(db, indent=4))


def aws_cp_get_dl_files_folder_content():
    fol = get_ddh_folder_path_dl_files()
    ls = glob.glob(f'{fol}/**/*', recursive=True)
    ls = [i for i in ls if os.path.isfile(i)]
    return {f: os.path.getsize(f) for f in ls if
            f.endswith('.lid') or
            f.endswith('.lix') or
            f.endswith('.csv') or
            f.endswith('.gps') or
            f.endswith('.cst') or
            f.endswith('.txt') or
            f.endswith('.bin')}


# this function is called after aws_sync() to build DB
def aws_cp_init():
    if os.path.exists(PATH_AWS_CP_DB):
        os.unlink(PATH_AWS_CP_DB)
    db = aws_cp_get_dl_files_folder_content()
    _inventory_save_to_file(db)


# function called after a file is successfully AWS copied
def aws_cp_add(file_name, file_size):
    try:
        db = _inventory_load_from_file()
        db[file_name] = file_size
        _inventory_save_to_file(db)
    except (IndexError, KeyError) as ex:
        print(f"error: db_aws_cp -=> {ex}")


# this function is probably never going to be used
def aws_cp_del(file_name):
    db = _inventory_load_from_file()
    if file_name in db.keys():
        del db[file_name]
    _inventory_save_to_file(db)


def aws_cp_compare_new_vs_database(d_new):
    d_diff = {}
    d_old = _inventory_load_from_file()
    for name, size in d_new.items():
        if name not in d_old.keys():
            d_diff[name] = size
        elif name in d_old.keys() and size != d_old[name]:
            d_diff[name] = size
    return d_diff


if __name__ == '__main__':
    aws_cp_init()
