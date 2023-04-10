class DDHStatus:

    """
    stores and reports DDH status, useful for pubsub data collection in VPN
    """

    def __init__(self):
        self.gps = "faba"

    def set_gps(self, g):
        self.gps = g

    def get_gps(self):
        return str(self.gps)


ddh_status = DDHStatus()
