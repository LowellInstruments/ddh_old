import subprocess as sp


def _sho(c):
    rv = sp.run(c, shell=True, stdout=sp.PIPE, stderr=sp.PIPE)
    return rv.returncode, rv.stdout


def cell_get_iccid():
    # data-sheet
    c = "echo -ne 'AT+QCCID\r' > /dev/ttyUSB2"
    _sho(c)
    c = "cat -v < /dev/ttyUSB2 | grep 2022"
    rv, s = _sho(c)
    return s.decode()
