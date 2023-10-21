import json
import socket
import time
from threading import Thread

from rpc.rpc_common import RPC_SIZE


class _RPCServer:
    def __init__(self,
                 host: str = '0.0.0.0',
                 port: int = 8080) -> None:
        self.host = host
        self.port = port
        self.address = (host, port)
        self._methods = {}

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
            print(f'\nRPC server {self.address} launched')

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
        self.register_method(self.file_touch)
        self.register_method(self.get_epoch)

    @staticmethod
    def file_touch(f):
        d = {
            'type': 'a',
            'uuid': 1,
            'v': f'created {f}'
        }
        return d

    @staticmethod
    def get_epoch():
        d = {
            'type': 'a',
            'uuid': 1,
            'v': str(int(time.time()))
        }
        return d


class DDHRPCNotifyServer(_RPCServer):
    def __init__(self):
        super().__init__(port=6901)
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
    s = DDHRPCCmdServer()
    s.run()


def srv_notify_fxn():
    s = DDHRPCNotifyServer()
    s.run()
