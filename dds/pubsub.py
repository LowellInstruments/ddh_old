import threading
import socket as sk
from dds.status import ddh_status


PORT_SUB_IN = 37020
PORT_PUB_IN = 37021


cli = sk.socket(sk.AF_INET, sk.SOCK_DGRAM, sk.IPPROTO_UDP)
cli.setsockopt(sk.SOL_SOCKET, sk.SO_REUSEPORT, 1)
cli.setsockopt(sk.SOL_SOCKET, sk.SO_BROADCAST, 1)


def _pub_fxn(cmd):
    svr = sk.socket(sk.AF_INET, sk.SOCK_DGRAM, sk.IPPROTO_UDP)
    svr.setsockopt(sk.SOL_SOCKET, sk.SO_REUSEPORT, 1)
    svr.setsockopt(sk.SOL_SOCKET, sk.SO_BROADCAST, 1)
    svr.bind(("", PORT_PUB_IN))
    svr.settimeout(1)
    svr.sendto(cmd.encode(), ("<broadcast>", PORT_SUB_IN))
    data, addr = svr.recvfrom(1024)
    print("pub_in {} from {}".format(data, addr[0]))
    svr.close()


def pubsub_run_pub():
    try:
        _pub_fxn("ping")
        _pub_fxn("status_gps")

    except (Exception,) as ex:
        print("pub exception", ex)


def _sub_fxn():
    cli.bind(("", PORT_SUB_IN))
    while 1:
        data, addr = cli.recvfrom(1024)

        # grab everything in advance
        g = ddh_status.get_gps()

        if data == b"ping":
            cli.sendto(b"pong", (addr[0], PORT_PUB_IN))
        if data == b"status_gps":
            cli.sendto(g.encode(), (addr[0], PORT_PUB_IN))

        print("sub_in", data)


def pubsub_run_sub():
    try:
        th = threading.Thread(target=_sub_fxn)
        th.start()
    except (Exception,):
        pass


if __name__ == "__main__":
    # only use threads for testing here
    pubsub_run_sub()
    th = threading.Thread(target=pubsub_run_pub)
    th.start()
