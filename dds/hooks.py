import pathlib
import shutil
from dds.macs import dds_create_folder_macs_color
from utils.ddh_config import dds_get_cfg_flag_purge_black_macs_on_boot
from utils.ddh_shared import get_ddh_folder_path_macs_black
from utils.logs import lg_dds as lg


def apply_debug_hooks():
    if dds_get_cfg_flag_purge_black_macs_on_boot():
        lg.a("debug: HOOK_PURGE_BLACK_MACS_ON_BOOT")
        p = pathlib.Path(get_ddh_folder_path_macs_black())
        shutil.rmtree(str(p), ignore_errors=True)
        dds_create_folder_macs_color()
