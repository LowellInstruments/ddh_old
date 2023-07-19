import serial.tools.list_ports


def find_usb_port_automatically(vp):
    # vp: vid_pid -> '1234:5678'
    vp = vp.upper()
    for p in serial.tools.list_ports.comports():
        info = dict({"Name": p.name,
                     "Description": p.description,
                     "Manufacturer": p.manufacturer,
                     "Hwid": p.hwid})
        if vp in info['Hwid']:
            return '/dev/' + info['Name']


if __name__ == '__main__':
    # GPS puck, it has 2 PID
    p = find_usb_port_automatically('067B:2303')
    print(p)
    p = find_usb_port_automatically('067B:23A3')
    print(p)
    # Rockblocks
    p = find_usb_port_automatically('0403:6001')
    print(p)
