import enum
import re
import time
from typing import Any, Literal, cast

from fit import logger
from fit.interfaces.gdb.controller import GDBController, gdb_response
from fit.interfaces.internal_injector import InternalInjector
from fit.mapping import Mapping

log = logger.get(__name__)

GDB_FLAGS = ["-q", "--nx", "--interpreter=mi3"]


def get_int(s: str, byteorder: Literal["little", "big"]) -> int:
    b = bytes.fromhex(s)
    return int.from_bytes(b, byteorder=byteorder)


def to_gdb_hex(i: int, byteorder: Literal["little", "big"]) -> str:
    s = hex(i).replace("0x", "")

    # Ensure even length (pairs of hex digits)
    if len(s) % 2 != 0:
        s = "0" + s

    byte_array = bytes.fromhex(s)
    if byteorder == "little":
        byte_array = byte_array[::-1]

    return "".join(f"{b:02x}" for b in byte_array)


class GDBInjector(InternalInjector):
    controller: GDBController

    gdb_path: str = "gdb_multiarch"

    register_names: list[str]

    embedded: bool = False

    endianness = cast(Literal["little", "big"], "little")

    word_size: int = 4

    class Breakpoint:
        id: int

        address: int

        name: str

        def __init__(
            self,
            id: int,
            address: int,
            name: str,
        ) -> None:
            self.id = id
            self.address = address
            self.name = name

    breakpoints: list[Breakpoint] = []

    class State(enum.Enum):
        STARTING = 0
        RUNNING = 1
        INTERRUPT = 2
        EXIT = 3

    state: State = State.STARTING

    def __init__(self, elf_path: str, **kwargs: dict[str, Any]) -> None:
        if "gdb_path" in kwargs and isinstance(kwargs["gdb_path"], str):
            self.gdb_path = kwargs["gdb_path"]

        self.controller = GDBController(
            command=[self.gdb_path, *GDB_FLAGS, elf_path],
        )

        self.controller.write("-gdb-set mi-async on")

        if "remote" in kwargs and isinstance(kwargs["remote"], str):
            self.remote(address=kwargs["remote"])

        if "embeded" in kwargs and isinstance(kwargs["embeded"], bool):
            self.embedded = kwargs["embeded"]

        if "word_size" in kwargs and isinstance(kwargs["word_size"], int):
            self.word_size = kwargs["word_size"]

        self.reset()

        r = self.controller.write(
            "-data-list-register-names",
            wait_for={
                "type": "result",
                "message": "done",
                "payload": {"register-names": []},
            },
        )

        self.register_names = r[0]["payload"]["register-names"]

    def reset(self) -> None:
        self.controller.write("-break-delete")

        if self.embedded:
            self.controller.write("-target-reset")

            """
                Perform a hard reset on the target. This calls the monitor command `jtag_reset` in the st-util gdb server. Then, since the target is in a reset state, we wait for the DHCSR register to indicate that the target is in a reset state. If the target is not in a reset state, we wait for 0.5 seconds and check again.
                The library cannot do this on its own because it can't access the usb device directly since it's already occupied by _this_ gdb server.

            These values _should_ be portable since stlink uses them for everything, so it might be a standard.

            TODO: In the case they aren't, we can just wait a bit and then continue the execution
            """
            self.controller.write(
                '-interpreter-exec console "monitor jtag_reset"',
                wait_for={
                    "type": "result",
                    "message": "done",
                    "payload": None,
                },
            )

            STM32_REG_DHCSR = 0xE000EDF0
            STM32_REG_DHCSR_S_RESET_ST = 1 << 25

            dhcsr = self.read_memory(STM32_REG_DHCSR)

            while (dhcsr & STM32_REG_DHCSR_S_RESET_ST) == 0:
                time.sleep(0.5)
                dhcsr = self.read_memory(STM32_REG_DHCSR)

        else:
            self.controller.write(
                '-interpreter-exec console "start"',
                wait_for={
                    "message": "breakpoint-deleted",
                    "payload": {"id": None},
                    "type": "notify",
                },
            )

    def is_running(self) -> bool:
        return self.state == self.State.RUNNING

    def remote(self, address: str) -> gdb_response:
        if ":" not in address:
            log.critical('Remote address must be in the format "host:port"')
        if not address.split(":")[1].isdigit():
            log.critical("Port must be an integer")

        if not self.controller:
            log.critical("GDB controller not initialized")

        return self.controller.write(f"-target-select extended-remote {address}")

    def set_event(self, event: str) -> None:
        """Set a handler for an event."""

        if not self.controller:
            log.critical("GDB controller not initialized")
        bp = self.controller.write(
            f"-break-insert {event}",
            wait_for={
                "message": "done",
                "payload": {"bkpt": {}},
                "type": "result",
            },
        )

        if not bp[0]["message"] == "done":
            log.critical("Error setting event")
        if not self.controller:
            log.critical("GDB controller not initialized")
        if self.is_running():
            log.critical("Injector is not running")

        self.breakpoints.append(
            self.Breakpoint(
                id=int(bp[0]["payload"]["bkpt"]["number"]),
                address=bp[0]["payload"]["bkpt"]["addr"],  ## TODO: actually parse this
                name=event,
            )
        )

    def read_memory(self, address: int) -> int:
        """Access memory at a given address."""

        if not self.controller:
            log.critical("GDB controller not initialized")
        if self.is_running():
            log.critical("Cannot read memory while process is running")

        r = self.controller.write(
            f"-data-read-memory-bytes {hex(address)} {self.word_size}",
            wait_for={
                "message": "done",
                "payload": {"memory": []},
                "stream": "stdout",
                "token": None,
                "type": "result",
            },
        )[0]

        if r["message"] != "done" or r["type"] != "result":
            print(r)

        return get_int(r["payload"]["memory"][0]["contents"], self.endianness)

    def write_memory(self, address: int, value: int) -> None:
        """Write a value to memory at a given address."""

        if not self.controller:
            log.critical("GDB controller not initialized")
        if self.is_running():
            log.critical("Cannot write memory while process is running")

        self.controller.write(
            f"-data-write-memory-bytes {hex(address)} {to_gdb_hex(value, 'little')}",
            wait_for={
                "message": "done",
                "payload": None,
                "type": "result",
            },
        )

    def read_register(self, register: str) -> int:
        """Read the value of a register."""

        if not self.controller:
            log.critical("GDB controller not initialized")
        if self.is_running() and self.state == self.State.EXIT:
            log.critical("Cannot read registers while process is running or has exited")

        r = self.controller.write(
            "-data-list-register-values d",
            wait_for={
                "message": "done",
                "payload": {"register-values": []},
                "type": "result",
            },
        )[0]

        idx = self.register_names.index(register)
        val = r["payload"]["register-values"][idx]

        if "value" in val:
            log.critical("Vector/Special registers not supported yet!")

        return int(val["value"])

    def write_register(self, register: str, value: int) -> None:
        """Write a value to a register."""

        if not self.controller:
            log.critical("GDB controller not initialized")
        if self.is_running() and self.state == self.State.EXIT:
            log.critical("Cannot write registers while process is running or has exited")

        self.controller.write(
            f'-interpreter-exec console "set ${register}={hex(value)}"',
            wait_for={
                "message": "done",
                "payload": None,
                "type": "result",
            },
        )

    def close(self) -> None:
        """Close the injector."""
        self.controller.write("-target-kill")

    def run(self, blocking: bool = False) -> str:
        """Run the injector for a given amount of time."""

        if not self.controller:
            log.critical("GDB controller not initialized")

        if self.is_running():
            log.warning("Injector is already running")

        self.state = self.State.RUNNING
        bp = self.controller.write("-exec-continue")

        while self.state == self.State.RUNNING:
            for msg in bp:
                if msg["message"] != "stopped":
                    continue

                if "reason" in msg["payload"] and msg["payload"]["reason"] == "exited-normally":
                    self.state = self.State.EXIT

                    return "exit"

                for b in self.breakpoints:
                    if b.id == int(msg["payload"]["bkptno"]):
                        self.state = self.State.INTERRUPT

                        return b.name

            if not blocking:
                break

            bp = self.controller.wait_response()

        self.state = self.State.EXIT
        return "unknown"

    def get_register_names(self) -> list[str]:
        return self.register_names

    def interrupt(self) -> None:
        self.controller.write("-exec-interrupt --all")
        self.state = self.State.INTERRUPT

    def get_mappings(self) -> list[Mapping]:
        self.controller.flush()
        mappings = self.controller.write(
            '-interpreter-exec console "info proc mappings"',
            wait_for={
                "message": "done",
                "payload": None,
                "type": "result",
            },
            whole_response=True,
        )
        perm_flags = {
            "r": Mapping.Permissions.READ,
            "w": Mapping.Permissions.WRITE,
            "x": Mapping.Permissions.EXEC,
            "p": Mapping.Permissions.PRIVATE,
        }

        res = []
        for line in mappings[3:-1]:
            parts = re.split(r"\s+", line["payload"])

            if len(parts) < 5:
                ## TODO: Log invalid mapping
                return []

            perms = 0
            for c, p in zip("rwxp", parts[4]):
                if p == c:
                    perms |= perm_flags[p]

            mapping = Mapping(
                int(parts[0], 16),
                int(parts[1], 16),
                int(parts[2], 16),
                int(parts[3], 16),
                perms,
                " ".join(parts[5:]) if len(parts) > 5 else "",
            )

            res.append(mapping)

        return res
