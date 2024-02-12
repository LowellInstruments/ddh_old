import os
import pathlib


FILE_SEMAPHORE_BLE_AWS = '/tmp/ble_aws.sem'


def _set_semaphore_file(f):
    pathlib.Path.touch(f)


def _clear_semaphore_file(f):
    try:
        os.unlink(f)
    except FileNotFoundError:
        # ex: file not found
        pass
    except (Exception, ) as ex:
        print(f'error: clear_semaphore_file -> {ex}')


def ble_aws_sem_set():
    return _set_semaphore_file(FILE_SEMAPHORE_BLE_AWS)


def ble_aws_sem_clr():
    return _clear_semaphore_file(FILE_SEMAPHORE_BLE_AWS)
