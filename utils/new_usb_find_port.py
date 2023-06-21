import serial.tools.list_ports


def find_usb_port_automatically(vid_pid):
    # vid_pid -> '1234:5678'

    port_data = []
    for port in serial.tools.list_ports.comports():
        info = dict({"Name": port.name, "Description": port.description, "Manufacturer": port.manufacturer,
                     "Hwid": port.hwid})
        if vid_pid in info['Hwid']:
            return '/dev/' + info['Name']


if __name__ == '__main__':
    # GPS puck
    p = find_usb_port_automatically('067B:2303')
    print(p)
    # Rockblocks
    p = find_usb_port_automatically('0403:6001')
