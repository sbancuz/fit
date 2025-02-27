from typing import Any, Dict, List

from pygdbmi.gdbcontroller import GdbController

# import logging

gdb_response = List[Dict[Any, Any]]

# logger = logging.basicConfig(
# )


class GDBController:
    controller: GdbController

    def __init__(self, command: List[str]) -> None:
        self.controller = GdbController(command=command)

    def write(self, command: str) -> gdb_response:
        # pprint(f'--> {command}')
        # logger.debug(f'--> {command}')
        r: gdb_response = self.controller.write(command)

        # pprint(f'<-- {r}')
        # logger.debug(f'<-- {r}')

        return r

    def wait_response(self) -> gdb_response:
        r: gdb_response = self.controller.get_gdb_response(raise_error_on_timeout=False)
        # pprint(f'<-- {r}')
        # logger.debug(f'<-- {r}')
        return r

    def exit(self) -> None:
        self.controller.exit()
