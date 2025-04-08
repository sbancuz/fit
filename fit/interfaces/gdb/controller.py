import logging
from typing import Any

from pygdbmi.gdbcontroller import GdbController

from fit import logger

log = logger.get()
gdb_response = list[dict[str, Any]]


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

    def write(
        self,
        command: str,
        wait_for: list[dict[str, Any]] | dict[str, Any] | None = None,
        whole_response: bool = False,
    ) -> gdb_response:
        log.debug(f"--> {command}")
        r: gdb_response = self.controller.write(command, raise_error_on_timeout=False)

        if wait_for is not None:
            return self.await_response(r, wait_for, whole_response)

        log.debug(f"<-- {r}")

        return r

    def flush(self) -> None:
        r: gdb_response = self.controller.get_gdb_response(raise_error_on_timeout=False)
        log.debug(f"<-- {r}")
        if r == []:
            return

    def wait_response(
        self,
        wait_for: list[dict[str, Any]] | dict[str, Any] | None = None,
        whole_response: bool = False,
    ) -> gdb_response:
        r: gdb_response = self.controller.get_gdb_response(raise_error_on_timeout=False)
        if wait_for is not None:
            return self.await_response(r, wait_for, whole_response)

        log.debug(f"<-- {r}")
        return r

    def exit(self) -> None:
        self.controller.exit()

    def await_response(
        self,
        request_response: gdb_response,
        wait_for: list[dict[str, Any]] | dict[str, Any],
        whole_response: bool = False,
    ) -> gdb_response:
        if isinstance(wait_for, dict):
            wait = [wait_for]
        else:
            wait = wait_for

        while True:
            log.debug(f"<-- {request_response}")

            for msg in request_response:
                if "message" in msg and msg["message"] == "error":
                    log.critical(f"{msg['payload']}")
                    return request_response

                for w in wait:
                    if check(msg, w):
                        if whole_response:
                            return request_response

                        return [msg]

            request_response = self.controller.get_gdb_response(raise_error_on_timeout=False)
