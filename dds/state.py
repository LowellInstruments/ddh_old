import os

from mat.utils import linux_is_rpi
from utils.logs import lg_sta as lg
from utils.ddh_shared import get_ddh_folder_path_tweak
import toml

FILE_SAVED_BRIGHTNESS = f'{get_ddh_folder_path_tweak()}/.saved_brightness.toml'


def state_get_saved_brightness():
    if not linux_is_rpi():
        return
    if not os.path.exists(FILE_SAVED_BRIGHTNESS):
        lg.a('creating brightness file with value 100, index 9')
        state_save_brightness(9)
    with open(FILE_SAVED_BRIGHTNESS, 'r') as f:
        d = toml.load(f)
        v = d['saved_brightness']
        lg.a(f'retrieving saved brightness {v}')
        return v


def state_save_brightness(v):
    d = dict()
    d['brightness'] = v
    with open(FILE_SAVED_BRIGHTNESS, 'w') as f:
        toml.dump(d, f)


def state_ble_init_rv_notes(d: dict):
    d["battery_level"] = 0xFFFF
    d["error"] = ""
    d["crit_error"] = 0
    d["dl_files"] = []
    d["rerun"] = False
    d["gfv"] = ''


def state_ble_logger_ccx26x2r_needs_a_reset(mac):
    mac = mac.replace(':', '-')
    r = get_ddh_folder_path_tweak()

    # checks existence of 'tweak/<mac>.rst' file
    file_path = f'{r}/{mac}.rst'
    rv = os.path.exists(file_path)
    if rv:
        lg.a("debug: logger reset file {} found".format(file_path))
        os.unlink(file_path)
        lg.a("debug: logger reset file {} deleted".format(file_path))
    return rv


class DdhState:
    def __init__(self):
        self.downloading_ble = False
        self.ble_reset_req = 0

    def state_set_downloading_ble(self): self.downloading_ble = 1
    def state_clr_downloading_ble(self): self.downloading_ble = 0
    def state_get_downloading_ble(self): return self.downloading_ble
    def state_set_ble_reset_req(self): self.ble_reset_req = 1
    def state_clr_ble_reset_req(self): self.ble_reset_req = 0
    def state_get_ble_reset_req(self): return self.ble_reset_req


ddh_state = DdhState()
