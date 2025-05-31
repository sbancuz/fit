import concurrent.futures
import time
from collections import defaultdict
from datetime import timedelta
from typing import Any, Callable, Type, overload

from fit import logger
from fit.csv import export_to_csv
from fit.elf import ELF
from fit.interfaces.implementations import Implementation
from fit.interfaces.internal_injector import InternalInjector
from fit.memory import IntList, Memory

log = logger.get()


def noop(_: Type["Injector"]) -> None:
    """
    No-operation function for default callbacks.

    :param _: Type of the Injector.
    """

    return


class Registers:
    """
    Class for interacting with CPU registers through an internal injector.
    """

    """The internal injector instance."""
    __internal_injector: InternalInjector
    """The parsed ELF binary."""
    elf: ELF
    """The registers."""
    registers: list[str]

    def __init__(self, injector: InternalInjector, bin: ELF) -> None:
        self.__internal_injector = injector
        self.elf = bin

        self.registers = self.__internal_injector.get_register_names()

    def __getitem__(self, name: str) -> int:
        """
        Gets the value of a register by name.

        :param name: the name of the register.
        :return: the register value.
        """

        if name.lower() not in self.registers:
            log.critical(f"Register {name} not found")

        return self.__internal_injector.read_register(name)

    def __setitem__(self, name: str, value: int | list[int] | IntList) -> None:
        """
        Sets the value of a register by name.

        :param name: the name of the register.
        :param value: the register value.
        """

        if name not in self.registers:
            log.critical(f"Register {name} not found")

        if isinstance(value, IntList) or isinstance(value, list):
            if len(value) > 1:
                log.critical(f"Register {name} is not an array")

            v = value[0]
        elif isinstance(value, int):
            v = value

        self.__internal_injector.write_register(name, v)


class Injector:
    """
    Class for managing the injection process into an ELF binary.
    """

    """The internal injector instance."""
    __internal_injector: InternalInjector
    """The parsed ELF binary."""
    binary: ELF
    """The memory."""
    memory: Memory
    """The registers."""
    regs: Registers

    class Event:
        """
        Class representing an event with a callback and arguments.
        """

        """The callback function to be executed."""
        callback: Callable[..., Any]
        """The additional arguments for the callback function."""
        kwargs: dict[str, Any]

        def __init__(self, callback: Callable[..., Any], **kwargs: dict[str, Any]) -> None:
            self.callback = callback
            self.kwargs = kwargs

    """The events."""
    events: dict[str, Event] = {}
    """The golden run. Dictionary with (target, value) pairs."""
    golden: dict[str, list[Any]] = {}
    """The injected run. Dictionary with (target, value) pairs."""
    runs: dict[str, list[Any]] = {}

    def __init__(
        self,
        bin: str,
        implementation: str = "gdb",
        **kwargs: Any,
    ) -> None:
        impl = Implementation.from_string(implementation)
        self.binary = ELF(bin)
        kwargs["word_size"] = self.binary.bits // 8

        self.__internal_injector = impl(bin, **kwargs)

        self.regs = Registers(self.__internal_injector, self.binary)
        self.memory = Memory(self.__internal_injector, self.binary)
        self.runs = defaultdict(list)
        self.golden = defaultdict(list)

    def reset(self) -> None:
        """
        Function that resets the internal injector instance.
        """

        self.__internal_injector.reset()

    def set_result_condition(
        self, event: str, callback: Callable[..., Any] = noop, **kwargs: dict[str, Any]
    ) -> None:
        """
        Function that sets a result condition for an event with a callback.

        :param event: the event name.
        :param callback: the callback function.
        :param kwargs: the additional arguments for the callback function.
        """

        self.__internal_injector.set_event(event)

        self.events[event] = self.Event(callback, **kwargs)

    @overload
    def run(self) -> str: ...

    @overload
    def run(self, timeout: timedelta) -> str: ...

    @overload
    def run(self, timeout: timedelta, injection_delay: timedelta) -> str: ...

    @overload
    def run(
        self,
        timeout: timedelta,
        injection_delay: timedelta,
        inject_func: Callable[..., Any],
    ) -> str: ...

    def run(
        self,
        timeout: timedelta | None = None,
        injection_delay: timedelta | None = None,
        inject_func: Callable[..., Any] | None = None,
    ) -> str:
        """
        Function that runs the injection process with optional timeout, injection delay, and injection function.

        :param timeout: the timeout for the injection process.
        :param injection_delay: the delay for the injection process.
        :param inject_func: the inject function for the injection process.
        :return: the result of the injection process.
        """

        if injection_delay is None or inject_func is None:
            ev = self.__internal_injector.run(blocking=True)
            self.events[ev].callback(self, **self.events[ev].kwargs)
            return ev

        with concurrent.futures.ThreadPoolExecutor() as executor:
            event: str | None = None
            """
            This means that the event was triggered before the injection could take place.
            TODO: Maybe we should return the event instead of 'unknown'? Should this be an error?
            """
            if (event := self.__internal_injector.run(blocking=False)) != "unknown":
                log.warning("Event triggered before injection")
                self.events[event].callback(self, **self.events[event].kwargs)

                return event

            time.sleep(injection_delay.total_seconds())
            if (event := self.__internal_injector.interrupt()) is not None:
                log.warning("Event triggered before injection")
                self.events[event].callback(self, **self.events[event].kwargs)

                return event

            inject_func(self)

            proc = executor.submit(self.__internal_injector.run, blocking=True)

            try:
                if timeout is None:
                    event = proc.result()
                else:
                    event = proc.result(timeout=timeout.total_seconds())
            except concurrent.futures.TimeoutError:
                return "Timeout"

            self.events[event].callback(self, **self.events[event].kwargs)

            return event

    def close(self) -> None:
        """
        Function that closes the internal injector instance.
        """

        self.__internal_injector.close()

    def add_run(self, result: dict[str, Any], golden: bool = False) -> None:
        """
        Function that adds a result from a run to the collection of runs.

        :param result: the result of the run.
        :param golden: the golden run.
        """

        for key, value in result.items():
            if isinstance(value, list):
                for val in value:
                    if val is None:
                        log.critical(f"Value for key {key} is None")

                    if isinstance(val, dict):
                        log.critical(f"Value for key {key} is a dictionary")
            else:
                if value is None:
                    log.critical(f"Value for key {key} is None")

                if isinstance(value, dict):
                    log.critical(f"Value for key {key} is a dictionary")

        if self.golden != {} and self.runs != {} and self.golden.keys() != result.keys():
            log.critical("Golden run and runs must have the same keys")

        if golden:
            for key, value in result.items():
                self.golden[key].append(value)
        else:
            for key, value in result.items():
                self.runs[key].append(value)

    ## TODO: Make a way better reporting function
    def report(self) -> None:
        """
        Function that reports the injection runs.
        """

        print("Golden:")
        for key, value in self.golden.items():
            print(f"{key}: {value}")

        print("Runs:")
        for key, value in self.runs.items():
            for i, run in enumerate(value):
                print(f"{key} ({i}): {run}")

    def save(self, path: str) -> None:
        """
        Function that saves the runs to CSV files.

        :param path: the path to the CSV file.
        """

        path = path.split(".csv")[0] + ".csv"
        golden_path = path.split(".csv")[0] + "_golden.csv"

        if self.golden != {}:
            export_to_csv(golden_path, self.golden)
            log.info(f"Saving golden run to: {golden_path}")

        if self.runs != {}:
            export_to_csv(path, self.runs)
            log.info(f"Saving runs to: {path}")
