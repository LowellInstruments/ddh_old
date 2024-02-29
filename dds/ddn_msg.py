# ---------------------------
# old v1 notification system
# ---------------------------


OPCODE_SQS_DDH_BOOT = 'DDH_BOOT'
OPCODE_SQS_DDH_NEEDS_UPDATE = 'DDH_NEEDS_UPDATE'
OPCODE_SQS_DDH_ALARM_S3 = 'DDH_ALARM_S3'
OPCODE_SQS_DDH_ERROR_BLE_HW = 'DDH_ERROR_BLE_HARDWARE'
OPCODE_SQS_DDH_ERROR_GPS_HW = 'DDH_ERROR_GPS_HARDWARE'
OPCODE_SQS_DDH_ALIVE = 'DDH_ALIVE'
OPCODE_SQS_LOGGER_DL_OK = 'LOGGER_DOWNLOAD'
OPCODE_SQS_LOGGER_ERROR_OXYGEN = 'LOGGER_ERROR_OXYGEN'
OPCODE_SQS_LOGGER_MAX_ERRORS = 'LOGGER_ERRORS_MAXED_RETRIES'
OPCODE_SQS_LOGGER_LOW_BATTERY = 'LOGGER_LOW_BATTERY'


class DdnMsg:
    def __init__(self, msg_ver=1):
        self.reason = None
        self.logger_mac = None
        self.logger_sn = None
        self.project = None
        self.vessel = None
        self.ddh_commit = None
        self.utc_time = None
        self.local_time = None
        self.box_sn = None
        self.hw_uptime = None
        self.gps_position = None
        self.platform = None
        self.msg_ver = msg_ver
        self.data = None
