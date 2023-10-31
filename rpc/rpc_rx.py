import json
import os
import socket
import threading
import time
from threading import Thread

from rpc.rpc_common import RPC_SIZE


class DDHRPCCmdAns:
    def __init__(self, v, type_of='a', uuid=1):
        self.d = {
            'type': type_of,
            'uuid': uuid,
            'value': v
        }


class _RPCServer:
    def __init__(self,
                 host: str = '0.0.0.0',
                 port: int = 8080) -> None:
        self.host = host
        self.port = port
        self.address = (host, port)
        self._methods = {}
        self.type_of = ''

    def register_method(self, function) -> None:
        try:
            self._methods.update({function.__name__: function})
        except (Exception, ):
            raise Exception('pass only function objects')

    def __handle__(self,
                   client: socket.socket,
                   address: tuple):

        # called by run()
        while True:
            try:
                fxn, args, kwargs = json.loads(client.recv(RPC_SIZE).decode())
                print(f's -> req from {address}')
                print(f'     $ {fxn}({args})')
            except (Exception, ) as ex:
                # client disconnects
                break

            try:
                # -----------------------------
                # execute the incoming command
                # -----------------------------
                rsp = self._methods[fxn](*args, **kwargs)
                assert type(rsp) is dict
                client.sendall(json.dumps(rsp).encode())

            except (KeyError, ):
                # when asking for a non-registered command
                print(f'     $ well, i am NOT doing that')

        client.close()

    def run(self) -> None:
        with socket.socket(socket.AF_INET,
                           socket.SOCK_STREAM) as sock:
            # listen in this socket
            sock.setsockopt(socket.SOL_SOCKET,
                            socket.SO_REUSEADDR, 1)
            sock.bind(self.address)
            sock.listen()
            print(f'\n{self.type_of} {self.address} launched')

            while True:
                try:
                    # serve the petition via thread
                    cli, addr = sock.accept()
                    Thread(target=self.__handle__,
                           args=[cli, addr]).start()
                except KeyboardInterrupt:
                    break


class DDHRPCCmdServer(_RPCServer):
    def __init__(self):
        super().__init__(port=6900)
        self.type_of = 'RPC CMD Server'
        self.register_method(self.file_touch)
        self.register_method(self.get_epoch)
        self.register_method(self.get_work_dir)

    @staticmethod
    def file_touch(f):
        return DDHRPCCmdAns(f'created {f}').d

    @staticmethod
    def get_epoch():
        return DDHRPCCmdAns(str(int(time.time()))).d

    @staticmethod
    def get_work_dir():
        return DDHRPCCmdAns(os.getcwd()).d


class DDHRPCNotifyServer(_RPCServer):
    def __init__(self):
        super().__init__(port=6901)
        self.type_of = 'RPC Notifications Server'
        self.register_method(self.put_event)

    @staticmethod
    def put_event(s):
        d = {
            'type': 'a',
            'uuid': 1,
            'v': f'received event {s}'
        }
        return d


def srv_cmd_fxn():
    # DDS receives commands from remote DDH GUI
    s = DDHRPCCmdServer()
    s.run()


def srv_notify_fxn():
    # DDH GUI receives notifications from remote DDS
    s = DDHRPCNotifyServer()
    s.run()


def th_srv_cmd():
    while 1:
        th_sc = threading.Thread(target=srv_cmd_fxn)
        th_sc.start()
        th_sc.join()


def th_srv_notify():
    th_sn = threading.Thread(target=srv_notify_fxn)
    th_sn.start()
