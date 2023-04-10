import pyudev


def is_usb_serial(
    device, vid=None, pid=None, vendor=None, serial=None, *args, **kwargs
):
    """Checks device to see if its a USB Serial device.
    The caller already filters on the subsystem being 'tty'.
    If serial_num or vendor is provided, then it will further check to
    see if the serial number and vendor of the device also matches.
    """
    if "ID_VENDOR" not in device.properties:
        return False
    if vid is not None:
        if device.properties["ID_VENDOR_ID"] != vid:
            return False
    if pid is not None:
        if device.properties["ID_MODEL_ID"] != pid:
            return False
    if vendor is not None:
        if "ID_VENDOR" not in device.properties:
            return False
        if not device.properties["ID_VENDOR"].startswith(vendor):
            return False
    if serial is not None:
        if "ID_SERIAL_SHORT" not in device.properties:
            return False
        if not device.properties["ID_SERIAL_SHORT"].startswith(serial):
            return False
    return True


def extra_info(device):
    extra_items = []
    if "ID_VENDOR" in device.properties:
        extra_items.append("vendor '%s'" % device.properties["ID_VENDOR"])
    if "ID_SERIAL_SHORT" in device.properties:
        extra_items.append("serial '%s'" % device.properties["ID_SERIAL_SHORT"])
    if extra_items:
        return " with " + " ".join(extra_items)
    return ""


def list_devices(vid=None, pid=None, vendor=None, serial=None, *args, **kwargs):
    devs = []
    context = pyudev.Context()
    for device in context.list_devices(subsystem="tty"):
        if is_usb_serial(device, vid=vid, pid=pid, vendor=vendor, serial=serial):
            devs.append(
                [
                    device.properties["ID_VENDOR_ID"],
                    device.properties["ID_MODEL_ID"],
                    extra_info(device),
                    device.device_node,
                ]
            )
    return devs


# for testing
if __name__ == "__main__":
    list_devices()
