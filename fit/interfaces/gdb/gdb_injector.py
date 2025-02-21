from fit.interfaces.injector import InternalInjector
from fit.interfaces.gdb.controller import GdbController, gdb_response

from typing import Callable

GDB_FLAGS = ['-q', '--nx', '--interpreter=mi3']

class GDBIjector(InternalInjector):

    controller: GdbController

    gdb_path: str = 'gdb_multiarch'

    def __init__(self, elf_path: str, **kwargs) -> None:

        if 'gdb_path' in kwargs:
            self.gdb_path = kwargs['gdb_path']


        self.controller = GdbController(
            command=[
                self.gdb_path,
                *GDB_FLAGS,
                elf_path
            ],
        )

        if 'remote' in kwargs:
            self.remote(address=kwargs['remote'])

    def reset(self):
        pass

    def is_running(self) -> bool:
        return False

    def remote(self, address: str) -> gdb_response:
        assert ':' in address, 'Remote address must be in the format "host:port"'
        assert address.split(':')[1].isdigit(), 'Port must be an integer'

        assert self.controller, 'GDB controller not initialized'
        
        return self.controller.write(f'-target-select remote {address}')

    def set_event(self, event: str, callback: Callable, **kwargs) -> None:
        """Set a handler for an event."""

    def read_memory(self, address: int) -> int:
        """Access memory at a given address."""

        return 0

    def write_memory(self, address: int, value: int) -> None:
        """Write a value to memory at a given address."""

    def read_register(self, register: str) -> int:
        """Read the value of a register."""

        return 0

    def write_register(self, register: str, value: int) -> None:
        """Write a value to a register."""
