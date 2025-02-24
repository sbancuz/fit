from fit.interfaces.internal_injector import InternalInjector
from fit.interfaces.gdb.controller import GDBController, gdb_response

from typing import Callable, Literal

GDB_FLAGS = ['-q', '--nx', '--interpreter=mi3']

def get_int(s: str, byteorder: Literal['little', 'big']) -> int:
    b = bytes.fromhex(s)
    return int.from_bytes(b, byteorder=byteorder)

def to_gdb_hex(i: int) -> str:
    s = hex(i).replace('0x', '')
    if len(s) % 2 != 0:
        s = '0' + s

    return s

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

    breakpoints: list[Breakpoint] = []

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
            self.controller.write('-interpreter-exec console "monitor reset"')

    def is_running(self) -> bool:
        return True

    def remote(self, address: str) -> gdb_response:
        assert ':' in address, 'Remote address must be in the format "host:port"'
        assert address.split(':')[1].isdigit(), 'Port must be an integer'

        assert self.controller, 'GDB controller not initialized'
        
        return self.controller.write(f'-target-select remote {address}')

    def set_event(self, event: str, callback: Callable, **kwargs) -> None:
        """Set a handler for an event."""

        assert self.controller, 'GDB controller not initialized'
        bp = self.controller.write(f'-break-insert {event}')

        assert bp[0]['message'] == 'done', 'Error setting event'

        self.breakpoints.append(self.Breakpoint(
                id=bp[0]['payload']['bkpt']['number'],
                address=bp[0]['payload']['bkpt']['addr'],
                name=event,
                callback=callback,
                kwargs=kwargs,
        ))

    def read_memory(self, address: int, word_size: int) -> int:
        """Access memory at a given address."""

        assert self.controller, 'GDB controller not initialized'

        r = self.controller.write(f'-data-read-memory-bytes {hex(address)} {word_size}')[0]
        if r['message'] != 'done' or r['type'] != 'result':
            print(r)

        return get_int(r['payload']['memory'][0]['contents'], 'little')

    def write_memory(self, address: int, value: int) -> None:
        """Write a value to memory at a given address."""

        assert self.controller, 'GDB controller not initialized'

        self.controller.write(f'-data-write-memory-bytes {hex(address)} {to_gdb_hex(value)}')

    def read_register(self, register: str) -> int:
        """Read the value of a register."""

        assert self.controller, 'GDB controller not initialized'

        r = self.controller.write(f'-data-list-register-values d')[0]

        assert r['message'] == 'done', 'Error reading register values'
        idx = self.register_names.index(register)

        val = r['payload']['register-values'][idx]
        assert 'value' in val,  'Vector/Special registers not supported yet!'

        return int(val['value'])

    def write_register(self, register: str, value: int) -> None:
        """Write a value to a register."""

        assert self.controller, 'GDB controller not initialized'

        self.controller.write(f'-gdb-set ${register}={to_gdb_hex(value)}')

    def close(self) -> None:
        """Close the injector."""
        # self.controller.write('-target-disconnect')
        self.controller.write('-target-kill')

    def run(self) -> str:
        """Run the injector for a given amount of time."""

        assert self.controller, 'GDB controller not initialized'
        bp = self.controller.write('-exec-continue')

        for msg in bp:
            if msg['message'] != 'stopped':
                continue

            for b in self.breakpoints:
                # print(f'Breakpoint: {b.id}')
                # print(f'Address: {int(msg["payload"]["bkptno"])}')
                # print(f'Condition: {int(b.id) == int(msg["payload"]["bkptno"])} : {b.id} == {int(msg["payload"]["bkptno"])}')

                ## b.id is already an int so I have not fking idea why I'm casting it to int
                ## but if I don't do it, it doesn't work. I'm not sure why it doesn't work
                ## but I'm not going to spend more time on this.
                ##
                ## -- GitHub Copilot
                if int(b.id) == int(msg['payload']['bkptno']):
                    b.callback(*b.kwargs)
                    return b.name

        return 'unknown'

    def get_register_names(self) -> list[str]:
        return self.register_names

