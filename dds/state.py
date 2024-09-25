class DdhState:
    def __init__(self):
        self.downloading_ble = False

    def set_downloading_ble(self, v):
        self.downloading_ble = bool(v)

    def get_downloading_ble(self):
        return self.downloading_ble


ddh_state = DdhState()
