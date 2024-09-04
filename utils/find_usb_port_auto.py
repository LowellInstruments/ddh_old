import serial.tools.list_ports


def find_usb_port_automatically(vp):
    # vp: vid_pid -> '1234:5678'
    vp = vp.upper()
    for p in serial.tools.list_ports.comports():
        info = dict({"Name": p.name,
                     "Description": p.description,
                     "Manufacturer": p.manufacturer,
                     "Hwid": p.hwid})
        # careful this starts from 3 to 0
        if vp in info['Hwid']:
            return '/dev/' + info['Name']


def find_n_list_all_usb_port_automatically(vp):
    # vp: vid_pid -> '1234:5678'
    vp = vp.upper()
    ls = []
    for p in serial.tools.list_ports.comports():
        info = dict({"Name": p.name,
                     "Description": p.description,
                     "Manufacturer": p.manufacturer,
                     "Hwid": p.hwid})
        if vp in info['Hwid']:
            ls.append('/dev/' + info['Name'])
    return ls


if __name__ == '__main__':
    # GPS puck, it has 2 PID
    # p = find_usb_port_automatically('067B:2303')
    # print(p)
    # p = find_usb_port_automatically('067B:23A3')
    # print(p)

    # quectel shield
    # p = find_usb_port_automatically('2c7c:0125')
    # print(p)
    rv = find_n_list_all_usb_port_automatically('2c7c:0125')
    print(rv)


