import datetime
import glob
import os
import time
import serial
from settings import ctx
from utils.ddh_shared import get_ddh_folder_path_rbl
from utils.logs import lg_rbl as lg
from ieee754 import IEEE754
from ctypes import cast, pointer, c_int, POINTER, c_float

from utils.new_usb_find_port import find_usb_port_automatically


def dds_create_folder_rbl():
    r = get_ddh_folder_path_rbl()
    os.makedirs(r, exist_ok=True)


def rbl_hex_str_to_hex_bytes(si):
    # si: '1122', bo: \x11\x22
    bo = bytes(bytearray.fromhex(si))
    return bo


def _ieee754_str_to_float(s) -> float:
    # s: 'c2dee418'
    # tool: https://www.h-schmidt.net/FloatConverter/IEEE754.html
    i = int(s, 16)
    cp = pointer(c_int(i))
    fp = cast(cp, POINTER(c_float))
    return fp.contents.value


def rbl_float_to_ieee754_str(fi: float) -> (str, float):
    # bs: bit string
    bs = IEEE754(fi, precision=1)
    # hs: hex string
    hs = bs.str2hex()
    hs = hs.rjust(8, "0")
    # fo: float output back
    fo = _ieee754_str_to_float(str(hs))
    return hs, fo


def float_to_bcd_str(fi: float) -> str:
    fo_s = "{:05.2f}".format(fi).replace(".", "")
    return fo_s.rjust(4, "0")


def rbl_build_emolt_msg_as_str(lat,
                               lon,
                               x85,
                               m_ver=1,
                               m_type=1) -> str:

    m_ver = "{:02x}".format(m_ver)
    m_type = "{:02x}".format(m_type)
    # careful, float does NOT format similar as binary
    m_lat, _ = rbl_float_to_ieee754_str(float(lat))
    m_lon, _ = rbl_float_to_ieee754_str(float(lon))
    m_utc_time = "{:08x}".format(int(time.time()))
    m_min_d_df_85 = float_to_bcd_str(x85.min_d_df_85)
    m_max_d_df_85 = float_to_bcd_str(x85.max_d_df_85)
    m_mean_d_df_85 = float_to_bcd_str(x85.mean_d_df_85)
    m_std_d_df_85 = float_to_bcd_str(x85.std_d_df_85)
    m_min_t_df_85 = float_to_bcd_str(x85.min_t_df_85)
    m_max_t_df_85 = float_to_bcd_str(x85.max_t_df_85)
    m_mean_t_df_85 = float_to_bcd_str(x85.mean_t_df_85)
    m_std_t_df_85 = float_to_bcd_str(x85.std_t_df_85)
    # todo ---> need to do haul_duration and lg_sn
    m_haul_duration = "{:06x}".format(0x333333)
    m_lg_sn = "{:08x}".format(0x44444444)
    m_lg_man_id = "{:02x}".format(1)
    m_lg_rssi = "{:02x}".format(0x70)
    m_lg_bat_level = "{:04x}".format(0x6666)

    full_msg = ("{}" * 18).format(
        m_ver,
        m_type,
        m_lat,
        m_lon,
        m_utc_time,
        m_min_d_df_85,
        m_max_d_df_85,
        m_mean_d_df_85,
        m_std_d_df_85,
        m_min_t_df_85,
        m_max_t_df_85,
        m_mean_t_df_85,
        m_std_t_df_85,
        m_haul_duration,
        m_lg_sn,
        m_lg_man_id,
        m_lg_rssi,
        m_lg_bat_level,
    )

    n = len(full_msg)
    if len(full_msg) % 2:
        lg.a("error: message length {} should be even".format(n))
    else:
        lg.a("OK: rbl_build_emolt_msg_as_str() -> {}".format(full_msg))
    return full_msg


def rbl_decode(b: bytes):
    assert type(b) is bytes
    b = b'\x01\x01B\x18\x00\x00\xc2\xa6\x00\x00d,I !\x10$\x80"\x83\x014"\x00#\x90#\x18'
    b += b"\x00i333DDDD\x01pff"
    a = b.hex()
    # decode it
    a[0:2]
    a[2:4]
    float(_ieee754_str_to_float(a[4:12]))
    float(_ieee754_str_to_float(a[12:20]))
    m_utc_time = int(a[20:28], 16)
    "{}.{}".format(a[28:30], a[30:32])
    "{}.{}".format(a[32:34], a[34:36])
    "{}.{}".format(a[36:38], a[38:40])
    "{}.{}".format(a[40:42], a[42:44])
    "{}.{}".format(a[44:46], a[46:48])
    "{}.{}".format(a[48:50], a[50:52])
    "{}.{}".format(a[52:54], a[54:56])
    "{}.{}".format(a[56:58], a[58:60])
    a[60:66]
    a[66:74]
    a[74:76]
    a[76:78]
    a[78:82]

    print("m_utc_time", datetime.datetime.utcfromtimestamp(m_utc_time))
    # print(locals())


def rbl_gen_file(data):

    # --------------------
    # generate a RBL file
    # --------------------
    if type(data) is not bytes:
        print("error, rbl_gen_file data is not of bytes type")
        return

    dds_create_folder_rbl()
    fol = str(get_ddh_folder_path_rbl())
    now = int(time.time())
    path = "{}/{}.rbl".format(fol, now)

    # ------------------------
    # notice the BINARY flag
    # ------------------------
    with open(path, "wb") as f:
        f.write(data)
    lg.a("generated RBL file {} with content {}".format(path, data))


class RblException(Exception):
    pass


def _adjust_for_testing(fol) -> str:
    cwd = os.getcwd()
    if cwd.endswith("/dds"):
        cwd = cwd.replace("/dds", "")
    fol = cwd + "/" + str(fol)
    return str(fol)


def _rbl_find_usb_port():
    return find_usb_port_automatically('0403:6001')


# _ck means check
def _ck(cond, rv, s):
    if not cond:
        s = "_ck error: cmd {} -> returned {}".format(s, rv)
        raise RblException(s)


# see: https://docs.rockblock.rock7.com/reference/sbdix
def _rbl_parse_sbdix(b):
    if not b:
        raise RblException("empty SBDIX")

    # b'AT+SBDIX\r\r\n+SBDIX: 32, 1, 2, 0, 0, 0\r\n\r\nOK\r\n'
    if "SBDIX:" not in b.decode():
        e = "error SBDIX incomplete -> {}".format(b)
        raise RblException(e)

    fields = b.split(b" ")
    if fields and len(fields) != 7:
        e = "error SBDIX, # fields is {}".format(len(fields))
        raise RblException(e)

    # a -> ['0,', '5,', '0,', '0,', '0,', '0']
    a = b.replace(b",", b"").decode().split()[2:8]
    mo_sts, mo_sn, mt_sts, mt_sn, mt_len, mt_q = a
    lg.a("SBDIX answer: ")
    lg.a("    mo_sts: {}".format(mo_sts))
    lg.a("    mo_sn : {}".format(mo_sn))
    lg.a("    mt_sts: {}".format(mt_sts))
    lg.a("    mt_sn : {}".format(mt_sn))
    lg.a("    mt_len: {}".format(mt_len))
    lg.a("    mt_q  : {}".format(mt_q))
    if int(mo_sts) <= 2:
        return 0
    lg.a("error: mo_sts > 2")
    return 1


def _rbl_send(data, fmt="bin"):

    # check data length
    if len(data) > 120:
        lg.a("error: data too long to send via satellite")
        return 1

    # check format
    if fmt == "bin" and type(data) is not bytes:
        lg.a("error: data format expected bytes is {}".format(type(data)))
        return 1

    # find USB port of the Rockblocks device
    node = _rbl_find_usb_port()
    sp = serial.Serial()
    sp.baudrate = 19200
    sp.timeout = 1
    sp.port = node
    try:
        sp.open()
    except (Exception,) as ex:
        lg.a("error: cannot open USB port at {} -> {}".format(node, ex))
        if "permission denied" in str(ex):
            lg.a("debug: $ usermod -a -G plugdev dialout $USER")
            lg.a("debug: and reboot")
        return 1

    # ------------------------------------------
    # several steps to send data via satellite
    # ------------------------------------------
    rv: int
    try:
        sp.write(b"AT\r")
        rv = sp.readall()
        _ck(b"AT\r\r\nOK\r\n", rv, "ping")

        # always required, disable flow control
        sp.write(b"AT&K0\r")
        rv = sp.readall()
        _ck(b"AT&K0\r\r\nOK\r\n", rv, "flow")

        # -----------------
        # send ascii text
        # -----------------
        if fmt == "ascii":
            data = str(data)
            data_to_send = "AT+SBDWT={}\r".format(data).encode()
            lg.a("trying to send data\n{}".format(data_to_send))
            sp.write(data_to_send)
            rv = sp.readall()
            cond = rv and rv.startswith(b"AT+SBDWT=")
            cond = cond and rv.endswith(b"\r\nOK\r\n")
            _ck(cond, rv, "sbdwt")

        # -----------------
        # send binary data
        # -----------------
        else:
            b = data
            lg.a("trying to satellite send SBDWB -> {}".format(b))
            _ = "AT+SBDWB={}\r".format(len(b)).encode()
            sp.write(_)
            rv = sp.readall()
            cond = rv and rv.startswith(_)
            cond = cond and rv.endswith(b"\r\nREADY\r\n")
            _ck(cond, rv, "sbdwb")
            crc = sum(b).to_bytes(2, "big")
            sp.write(b + crc + b"\r")
            rv = sp.readall()
            lg.a("answer to SBDWB -> {}".format(rv))
            # rv: will contain status of the transmission
            cond = cond and rv.endswith(b"\r\nOK\r\n")
            _ck(cond, rv, "send_binary_data")

        # initiate extended SBD session, basically get cmd answer
        sp.write(b"AT+SBDIX\r")
        time.sleep(20)
        sbd = sp.readall()
        rv = _rbl_parse_sbdix(sbd)
        _ck(rv == 0, rv, "sbdix")

    except (Exception,) as ex:
        lg.a(ex)
        rv = 1

    finally:
        if sp:
            sp.close()
        if rv == 0:
            lg.a("message sent successfully")
        else:
            lg.a("message could NOT be sent")
        return rv


def rbl_serve():

    # ------------------
    # collect RBL files
    # ------------------
    fol = get_ddh_folder_path_rbl()
    fol = _adjust_for_testing(fol)
    # lg.a('serving folder {}'.format(fol))
    files = glob.glob("{}/*.rbl".format(fol))

    for _ in files:
        # open as BINARY
        f = open(_, "rb")
        data = f.read()
        f.close()

        # --------------------------
        # try to send via satellite
        # --------------------------
        lg.a("serving file {}".format(os.path.basename(_)))
        rv = _rbl_send(data)
        if rv == 0:
            # delete RBL file
            os.unlink(_)


def rbl_loop():
    if not ctx.rbl_en:
        lg.a("warning: rbl_en disabled")
        return

    while 1:
        rbl_serve()
        time.sleep(600)


# for testing, does not generate a RBL file
if __name__ == "__main__":
    # _b = b'\x35\x36\x11\x22\x33\x44\x55'
    # _rbl_send(_b * 1, fmt='bin')
    rbl_decode(bytes())
