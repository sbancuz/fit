from typing import Any

from pygdbmi.gdbcontroller import GdbController

# import logging

gdb_response = list[dict[str, Any]]

# logger = logging.basicConfig(
# )


def check(data: dict[str, Any], wait_for: dict[str, Any]) -> bool:
    """
    Perform a deep check of the data against the wait_for dictionary. Each
    specified key must be present in the data. The values just need partial matching
    to be considered a match. So everything in datamust be in wait_for, but not
    everything in wait_for must be in data.
    """
    for key, value in wait_for.items():
        if key not in data:
            return False

        if value is None:
            continue

        if isinstance(value, dict):
            if not check(data[key], value):
                return False

        elif isinstance(value, list):
            for v in value:
                if isinstance(v, dict):
                    if not check(data[key], v):
                        return False

        elif data[key] != value:
            return False

    return True


class GDBController:
    controller: GdbController

    def __init__(self, command: list[str]) -> None:
        self.controller = GdbController(command=command)

    def write(self, command: str, wait_for: dict[str, Any] | None = None) -> gdb_response:
        # pprint(f'--> {command}')
        # logger.debug(f'--> {command}')
        r: gdb_response = self.controller.write(command)

        if wait_for is not None:
            while True:
                for msg in r:
                    if check(msg, wait_for):
                        return [msg]

                r = self.controller.get_gdb_response(raise_error_on_timeout=False)

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
