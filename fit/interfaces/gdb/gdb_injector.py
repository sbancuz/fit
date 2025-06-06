import enum
import re
import struct
import threading
import time
from typing import Any, Literal, cast

from fit import logger
from fit.interfaces.gdb.boards import BoardsFamilies
from fit.interfaces.gdb.controller import GDBController, gdb_response
from fit.interfaces.internal_injector import InternalInjector
from fit.mapping import Mapping

log = logger.get()

GDB_FLAGS = ["-q", "--nx", "--interpreter=mi3"]


def parse_memory(
    memory: list[dict[str, Any]],
    count: int,
    word_size: int,
    endianness: Literal["little", "big"],
) -> list[int]:
    remainder = count % word_size
    size = count // word_size + (1 if remainder > 0 else 0)
    size = size if size > 0 else word_size
    res = [0 for _ in range(size)]
    for chunk in memory:
        off = int(chunk["offset"], 16)
        stop = int(chunk["end"], 16)
        begin = int(chunk["begin"], 16)

        val = chunk["contents"]
        last = (stop - begin) // word_size
        for i in range(last):
            ## We do word_size * 2 since in text 2 chars are a byte
            ini = i * word_size * 2
            end = (i + 1) * word_size * 2
            res[off + i] = get_int(val[ini:end], endianness)

        if remainder > 0:
            ## Convert to index like above
            last = last * word_size * 2
            res[-1] = get_int(val[last : last + remainder * 2], endianness)

    return res


def get_int(s: str, byteorder: Literal["little", "big"]) -> int:
    """
    Function that converts a hex string to an integer.

    :param s: the hex string to convert.
    :param byteorder: the endianness of the string (little or big).
    :return: the integer value
    """

    b = bytes.fromhex(s)
    return int.from_bytes(b, byteorder=byteorder)


def to_gdb_hex(i: list[int], byteorder: Literal["little", "big"], word_size: int) -> str:
    """
    Function that converts an integer to hex string.

    :param i: the integer to convert.
    :param byteorder: the endianness of the string (little or big).
    :return: the hex string representation of the integer value.
    """

    bits = "I" if word_size == 4 else "Q"
    endiannes = "<" if byteorder == "little" else ">"

    byte_array = struct.pack(endiannes + bits * len(i), *i)

    # if byteorder == "big":
    #     byte_array = byte_array[::-1]

    return "".join(f"{b:02x}" for b in byte_array)


class GDBInjector(InternalInjector):
    """
    Class that implements the GDB interface of the InternalInjector class.
    """

    """Handles direct GDB MI communication."""
    controller: GDBController
    """Path to the GDB executable. Defaults to 'gdb_multiarch'."""
    gdb_path: str = "gdb_multiarch"
    """List of available register names."""
    register_names: list[str]
    """Indicates if the target is an embedded device."""
    embedded: bool = False
    """Enum representing known embedded board families."""
    board_family: BoardsFamilies = BoardsFamilies.UNKNOWN
    """Endianness of the target architecture."""
    endianness = cast(Literal["little", "big"], "little")
    """Word size in bytes."""
    word_size: int = 4

    class Breakpoint:
        """
        Class that represents the breakpoint set in the target binary.
        """

        """Breakpoint identifier."""
        id: int
        """Breakpoint address."""
        address: int
        """Breakpoint name."""
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

    """List of breakpoints."""
    breakpoints: list[Breakpoint] = []

    class State(enum.Enum):
        """
        Enumeration class that enums all possible states.
        """

        STARTING = 0
        RUNNING = 1
        INTERRUPT = 2
        EXIT = 3

    """Current state."""
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

        if "embedded" in kwargs and isinstance(kwargs["embedded"], bool):
            self.embedded = kwargs["embedded"]

            if self.embedded:
                if (
                    "board_family" in kwargs
                    and isinstance(kwargs["board_family"], str)
                    and kwargs["board_family"].upper() in BoardsFamilies.__members__
                ):
                    self.board_family = BoardsFamilies[kwargs["board_family"].upper()]
                else:
                    log.warning(
                        f"Board family not recognized: {kwargs['board_family']}, defaulting to `UNKNOWN`"
                    )
                    log.warning("List of supported board families:")
                    for family in BoardsFamilies:
                        log.warning(f" - {family.name}")

                    self.board_family = BoardsFamilies.UNKNOWN

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

    def reset_stm32(self) -> None:
        """
        Function that performs a hard reset on the target. This calls the monitor command `jtag_reset` in the st-util gdb server. Then, since the target is in a reset state, we wait for the DHCSR register to indicate that the target is in a reset state. If the target is not in a reset state, we wait for 0.5 seconds and check again.
        The library cannot do this on its own because it can't access the usb device directly since it's already occupied by _this_ gdb server.

        These values _should_ be portable since stlink uses them for everything, so it might be a standard.
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

        dhcsr = self.read_memory(STM32_REG_DHCSR, self.word_size)[0]

        while (dhcsr & STM32_REG_DHCSR_S_RESET_ST) == 0:
            time.sleep(0.5)
            dhcsr = self.read_memory(STM32_REG_DHCSR, self.word_size)[0]

    def reset_unknown(self) -> None:
        """
        Function that perform a soft reset on the target. This calls the monitor command `reset` in the st-util gdb server.
        """

        self.controller.write(
            '-interpreter-exec console "monitor reset"',
            wait_for={
                "type": "result",
                "message": "done",
                "payload": None,
            },
        )

        ## Wait for the target to be in a reset state, it's not clear whether this is enough of a delay
        log.warning(
            "Resetting on unknown board family, waiting for 1 second for the reset to take effect..."
        )
        time.sleep(1)

    """Reset functions."""
    reset_functions = {
        BoardsFamilies.STM32: reset_stm32,
        BoardsFamilies.UNKNOWN: reset_unknown,
    }

    def reset(self) -> None:
        """
        Function that resets the injector to a known initial state. Useful between test runs or injections.
        """

        self.controller.write("-break-delete")

        if self.embedded:
            self.controller.write("-target-reset")

            self.reset_functions[self.board_family](self)

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
        """
        Function that checks if the target is running.

        :return: True if the target is running.
        """

        return self.state == self.State.RUNNING

    def remote(self, address: str) -> gdb_response:
        """
        Function that connects to a remote GDB server.

        :param address: the remote address in 'host:port' format.
        :return: the GDB response payload.
        """

        if ":" not in address:
            log.critical('Remote address must be in the format "host:port"')
        if not address.split(":")[1].isdigit():
            log.critical("Port must be an integer")

        if not self.controller:
            log.critical("GDB controller not initialized")

        return self.controller.write(f"-target-select extended-remote {address}")

    def set_event(self, event: str) -> None:
        """
        Function that sets a specific event for this target.

        :param event: the event to set.
        """

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

    def read_memory(self, address: int, count: int) -> list[int]:
        """
        Function that reads a memory word from the target.

        :param address: the memory address to read from.
        :param count: the number of bytes to read.
        :return: the value read from the target.
        """

        if not self.controller:
            log.critical("GDB controller not initialized")
        if self.is_running():
            log.critical("Cannot read memory while process is running")

        r = self.controller.write(
            f"-data-read-memory-bytes {hex(address)} {count}",
            wait_for={
                "message": "done",
                "payload": {"memory": []},
                "stream": "stdout",
                "token": None,
                "type": "result",
            },
        )[0]

        if len(r["payload"]["memory"]) > 1:
            log.warning("Tried to read unreadable memory, filling the gaps with 0")

        return parse_memory(r["payload"]["memory"], count, self.word_size, self.endianness)

    def write_memory(self, address: int, value: list[int], repeat: int) -> None:
        """
        Function that writes a memory word from the target.

        :param address: the memory address to write to.
        :param value: the value to write.
        """

        if not self.controller:
            log.critical("GDB controller not initialized")
        if self.is_running():
            log.critical("Cannot write memory while process is running")

        self.controller.write(
            f"-data-write-memory-bytes {hex(address)} {to_gdb_hex(value, self.endianness, self.word_size)} {hex(repeat)[2:]}e",
            wait_for={
                "message": "done",
                "payload": None,
                "type": "result",
            },
        )

    def read_register(self, register: str) -> int:
        """
        Function that reads a register from the target.

        :param register: the register to read.
        :return: the value read from the target.
        """

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
        """
        Function that writes a register from the target.

        :param register: the register to write.
        :param value: the value to write.
        """

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
        """
        Function that closes the GDB session and exit the controller.
        """

        self.controller.exit()

    def run(self, blocking: bool = False, stop_event: threading.Event | None = None) -> str:
        """
        Function that runs the injector for a given amount of time.

        :param blocking: whether to block until the precess stops.
        :return: the name of the breakpoint hit.
        """

        if not self.controller:
            log.critical("GDB controller not initialized")

        if self.is_running():
            log.warning("Injector is already running")

        self.state = self.State.RUNNING

        to_await: list[dict[str, Any]] = [
            {"type": "result", "message": "running", "payload": None},
            {
                "type": "notify",
                "message": "stopped",
                "payload": {"reason": "breakpoint-hit", "bkptno": None},
            },
        ]

        bp = self.controller.write(
            "-exec-continue",
            wait_for=to_await,
            whole_response=True,
        )

        while self.state == self.State.RUNNING:
            if stop_event and stop_event.is_set():
                return "Timeout"

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

            bp = self.controller.wait_response(
                wait_for=to_await, whole_response=True, stop_event=stop_event
            )

        self.state = self.State.EXIT
        return "unknown"

    def get_register_names(self) -> list[str]:
        """
        Function that returns a list of registers names.

        :return: the list of registers names.
        """

        return self.register_names

    def interrupt(self) -> str | None:
        """
        Function that interrupts the running process.
        """
        self.state = self.State.INTERRUPT
        r = self.controller.write(
            "-exec-interrupt --all",
            wait_for=[
                {
                    "type": "notify",
                    "message": "stopped",
                    "payload": {
                        "reason": "signal-received",
                        "signal-name": "SIGINT",
                        "signal-meaning": "Interrupt",
                        "frame": {},
                        "thread-id": None,
                    },
                },
                {
                    "type": "notify",
                    "message": "stopped",
                    "payload": {"reason": "breakpoint-hit", "bkptno": None},
                },
                {
                    "type": "notify",
                    "message": "stopped",
                    "payload": {
                        "reason": "signal-received",
                        "signal-name": "SIGTRAP",
                        "signal-meaning": "Trace/breakpoint trap",
                    },
                },
            ],
        )

        self.state = self.State.INTERRUPT

        if r[0]["message"] == "stopped" and r[0]["payload"]["reason"] == "breakpoint-hit":
            for b in self.breakpoints:
                if b.id == int(r[0]["payload"]["bkptno"]):
                    self.state = self.State.INTERRUPT
                    return b.name

        return None

    def get_mappings(self) -> list[Mapping]:
        """
        Function that retrieves memory mappings using GDB's 'info proc mappings'

        :return: the list of memory mappings.
        """

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
