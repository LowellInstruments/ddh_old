import json
import socket

from rpc.rpc_common import RPC_SIZE


class _RPCClient:
    def __init__(self,
                 host: str = 'localhost',
                 port: int = 8080):
        self.sk = None
        self.addr = (host, port)

    def connect(self):
        self.sk = socket.socket(socket.AF_INET,
                                socket.SOCK_STREAM)
        self.sk.settimeout(1)
        self.sk.connect(self.addr)

    def disconnect(self):
        try:
            self.sk.close()
        except (Exception, ):
            pass

    def __getattr__(self, __name: str):
        def execute(*args, **kwargs):
            print('\nc <-', __name, args)
            # todo ---> add a uuid here
            # kwargs['uuid'] = 1
            self.sk.sendall(json.dumps((__name, args, kwargs)).encode())
            try:
                rsp = json.loads(self.sk.recv(RPC_SIZE).decode())
                print('c ->', rsp)
                return rsp
            except socket.timeout:
                print('c -> timeout')
        return execute


class DDHRPCCmdClient(_RPCClient):
    def __init__(self):
        super().__init__(port=6900)


class DDHRPCNotifier(_RPCClient):
    def __init__(self):
        super().__init__(port=6901)


def cli_cmd_fxn():
    c = DDHRPCCmdClient()
    c.connect()
    c.file_touch('my_file')
    c.get_epoch()
    c.disconnect()


def cli_notify_fxn():
    c = DDHRPCNotifier()
    c.connect()
    c.put_event('client_notifies')
    c.file_touch('my_file')
    c.put_event('client_notifies')
    c.disconnect()

