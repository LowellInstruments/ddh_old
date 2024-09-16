import toml
import os
from ddh_config import _get_config_file_path


def exp_load_from_file():
    try:
        p = _get_config_file_path()
        with open(p, 'r') as f:
            c = toml.load(f)
            return c['experimental']
    except (Exception, ) as ex:
        print(f'error: exp_load_from_file {ex}')
        os._exit(1)


exp = exp_load_from_file()


def _get_key_from_exp(k):
    if not exp:
        return
    try:
        return exp[k]
    except (Exception, ) as ex:
        print(f'error: _get_key_from_exp -> {ex}')
        # not value, but indicates error
        return -1


def exp_get_use_lsb_for_tdo_loggers():
    return _get_key_from_exp('use_lsb_for_tdo_loggers')



if __name__ == '__main__':
    print(exp_get_use_lsb_for_tdo_loggers())
