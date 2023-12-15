import toml
import os

PATH_FILE_CFG = 'settings/config.toml'


def cfg_check_file_integrity():
    try:
        with open(PATH_FILE_CFG, 'r') as f:
            toml.load(f)
        return True
    except (Exception, ) as ex:
        print('error: toml_cfg_check_file_integrity: ', ex)


def cfg_read_file():
    try:
        with open(PATH_FILE_CFG, 'r') as f:
            return toml.load(f)
    except (Exception, ) as ex:
        print('error: toml_cfg_read_file: ', ex)
        os._exit(1)


if __name__ == '__main__':
    # change from <path>/ddh/utils to ddh
    os.chdir('..')
    cfg_check_file_integrity()
    cfg = cfg_read_file()
    print(cfg['behavior'])
