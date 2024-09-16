from mat.ble.ble_mat_utils import ble_mat_get_antenna_type_v2


class DdhState:
    def __init__(self):
        # some things are not ready at boot
        self.ble_antenna_i = None
        self.ble_antenna_s = None
        self.downloading_ble = False

    def refresh(self):
        self.ble_antenna_i, self.ble_antenna_s = ble_mat_get_antenna_type_v2()

    def set_downloading_ble(self, v):
        self.downloading_ble = bool(v)

    def get_downloading_ble(self):
        return self.downloading_ble

    def get_ble_antenna_i(self):
        return self.ble_antenna_i

    def get_ble_antenna_s(self):
        return self.ble_antenna_s


ddh_state = DdhState()
