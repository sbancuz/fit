
from pygdbmi.gdbcontroller import GdbController
from typing import List, Dict

gdb_response = List[Dict[None, None]]

class GDBController:

    controller: GdbController

    def __init__(self, command: List[str]) -> None:
        self.controller = GdbController(command=command)

    def write(self, command: str) -> gdb_response:
        logger.debug(f'--> {command}')
        r = self.controller.write(command)
        logger.debug(f'<-- {r}')

        return r

    def wait_response(self) -> gdb_response:
        r = self.controller.get_gdb_response()
        logger.debug(f'<-- {r}')
        return r

    def exit(self) -> None:
        self.controller.exit()
