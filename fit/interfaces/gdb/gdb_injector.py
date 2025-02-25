from fit.interfaces.internal_injector import InternalInjector
from fit.interfaces.gdb.controller import GDBController, gdb_response

from typing import Callable, Literal

GDB_FLAGS = ['-q', '--nx', '--interpreter=mi3']

def get_int(s: str, byteorder: Literal['little', 'big']) -> int:
    b = bytes.fromhex(s)
    return int.from_bytes(b, byteorder=byteorder)

def to_gdb_hex(i: int, byteorder: Literal['little', 'big']) -> str:
    s = hex(i).replace('0x', '')
    
    # Ensure even length (pairs of hex digits)
    if len(s) % 2 != 0:
        s = '0' + s

    byte_array = bytes.fromhex(s)
    if byteorder == 'little':
        byte_array = byte_array[::-1]

    return ''.join(f'{b:02x}' for b in byte_array)

class GDBIjector(InternalInjector):

    controller: GDBController

    gdb_path: str = 'gdb_multiarch'

    register_names: list[str]

    embeded: bool = False

    class Breakpoint:

        id: int

        address: int

        name: str

        callback: Callable

        kwargs: dict


        def __init__(self, id: int, address: int, name: str, callback: Callable, **kwargs) -> None:
            self.id = id
            self.address = address
            self.name = name
            self.callback = callback
            self.kwargs = kwargs

    running: bool = False

    breakpoints: list[Breakpoint] = []

    stopped: bool = False

    def __init__(self, elf_path: str, **kwargs) -> None:

        if 'gdb_path' in kwargs:
            self.gdb_path = kwargs['gdb_path']

        self.controller = GDBController(
            command=[
                self.gdb_path,
                *GDB_FLAGS,
                elf_path
            ],
        )

        self.controller.write('-gdb-set target-async on')

        if 'remote' in kwargs:
            self.remote(address=kwargs['remote'])

        if 'embeded' in kwargs:
            self.embeded = kwargs['embeded']

        r = self.controller.write('-data-list-register-names')
        self.register_names = r[0]['payload']['register-names']

    def reset(self):
        self.controller.write('-break-delete')
        self.controller.write('-target-reset')

        if self.embeded:
            self.controller.write('-interpreter-exec console "monitor reset halt"')
        else:
            self.controller.write('-interpreter-exec console "start"')

    def is_running(self) -> bool:
        return self.running

    def remote(self, address: str) -> gdb_response:
        assert ':' in address, 'Remote address must be in the format "host:port"'
        assert address.split(':')[1].isdigit(), 'Port must be an integer'

        assert self.controller, 'GDB controller not initialized'
        
        return self.controller.write(f'-target-select extended-remote {address}')

    def set_event(self, event: str, callback: Callable, **kwargs) -> None:
        """Set a handler for an event."""

        assert self.controller, 'GDB controller not initialized'
        bp = self.controller.write(f'-break-insert {event}')

        assert bp[0]['message'] == 'done', 'Error setting event'
        assert not self.is_running()

        self.breakpoints.append(self.Breakpoint(
            id=int(bp[0]['payload']['bkpt']['number']),
            address=bp[0]['payload']['bkpt']['addr'], ## TODO: actually parse this
            name=event,
            callback=callback,
            kwargs=kwargs,
        ))

    def read_memory(self, address: int, word_size: int) -> int:
        """Access memory at a given address."""

        assert self.controller, 'GDB controller not initialized'
        assert not self.is_running()

        r = self.controller.write(f'-data-read-memory-bytes {hex(address)} {word_size}')[0]
        if r['message'] != 'done' or r['type'] != 'result':
            print(r)

        return get_int(r['payload']['memory'][0]['contents'], 'little')

    def write_memory(self, address: int, value: int) -> None:
        """Write a value to memory at a given address."""

        assert self.controller, 'GDB controller not initialized'
        assert not self.is_running()

        self.controller.write(f'-data-write-memory-bytes {hex(address)} {to_gdb_hex(value, 'little')}')

    def read_register(self, register: str) -> int:
        """Read the value of a register."""

        assert self.controller, 'GDB controller not initialized'
        ## TODO: Test if this is true on the board
        assert not self.is_running() and self.stopped, 'Cannot read registers after process has stopped'

        r = self.controller.write(f'-data-list-register-values d')[0]

        assert r['message'] == 'done', 'Error reading register values'
        idx = self.register_names.index(register)

        val = r['payload']['register-values'][idx]
        assert 'value' in val,  'Vector/Special registers not supported yet!'

        return int(val['value'])

    def write_register(self, register: str, value: int) -> None:
        """Write a value to a register."""

        assert self.controller, 'GDB controller not initialized'
        ## TODO: Test if this is true on the board
        assert not self.is_running() and self.stopped, 'Cannot write registers after process has stopped'

        self.controller.write(f'-gdb-set ${register}={to_gdb_hex(value, 'little')}')

    def close(self) -> None:
        """Close the injector."""
        assert not self.is_running()

        self.controller.write('-target-kill')

    def run(self) -> str:
        """Run the injector for a given amount of time."""

        assert self.controller, 'GDB controller not initialized'
        assert not self.is_running()

        self.running = True
        bp = self.controller.write('-exec-continue')

        for msg in bp:
            if msg['message'] != 'stopped':
                continue

            for b in self.breakpoints:
                if b.id == int(msg['payload']['bkptno']):
                    self.stopped = True
                    self.running = False

                    b.callback(*b.kwargs)
                    return b.name

        self.stopped = True
        self.running = False
        
        return 'unknown'

    def finish(self) -> str:
        """Run the injector for a given amount of time."""

        assert self.controller, 'GDB controller not initialized'
        assert not self.is_running()

        self.running = True
        bp = self.controller.write('-exec-continue')

        while self.running:
            for msg in bp:
                if msg['message'] != 'stopped':
                    continue

                if 'reason' in msg['payload'] and msg['payload']['reason'] == 'exited-normally':
                    self.stopped = True
                    self.running = False

                    return 'exit'

                for b in self.breakpoints:
                    if b.id == int(msg['payload']['bkptno']):
                        self.stopped = True
                        self.running = False

                        b.callback(*b.kwargs)
                        return b.name

            bp = self.controller.wait_response()

        ## Here it should be an error
        print("ERROR")
        self.stopped = True
        self.running = False

        return 'unknown'

    def get_register_names(self) -> list[str]:
        return self.register_names

    def interrupt(self) -> None:
        self.controller.write('-exec-interrupt --all')
        self.running = False

