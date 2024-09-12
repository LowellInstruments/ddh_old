from mat.quectel import detect_quectel_usb_ports


def main_qus():
    rv = detect_quectel_usb_ports()
    print(f'QUS -> {rv}')


if __name__ == '__main__':
    main_qus()
