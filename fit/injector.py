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
from fit.memory import Memory

log = logger.get(__name__)


def noop(_: Type["Injector"]) -> None:
    return


class Registers:
    __internal_injector: InternalInjector

    elf: ELF

    registers: list[str]

    def __init__(self, injector: InternalInjector, bin: ELF) -> None:
        self.__internal_injector = injector
        self.elf = bin

        self.registers = self.__internal_injector.get_register_names()

    def __getitem__(self, name: str) -> int:
        if name.lower() not in self.registers:
            raise ValueError(f"Register {name} not found")

        return self.__internal_injector.read_register(name)

    def __setitem__(self, name: str, value: int) -> None:
        if name not in self.registers:
            raise ValueError(f"Register {name} not found")

        self.__internal_injector.write_register(name, value)


class Injector:
    __internal_injector: InternalInjector

    binary: ELF

    memory: Memory

    regs: Registers

    class Event:
        callback: Callable[..., Any]
        kwargs: dict[str, Any]

        def __init__(self, callback: Callable[..., Any], **kwargs: dict[str, Any]) -> None:
            self.callback = callback
            self.kwargs = kwargs

    events: dict[str, Event] = {}

    golden: dict[str, Any] = {}

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

    def reset(self) -> None:
        self.__internal_injector.reset()

    def set_result_condition(
        self, event: str, callback: Callable[..., Any] = noop, **kwargs: dict[str, Any]
    ) -> None:
        self.__internal_injector.set_event(event)

        self.events[event] = self.Event(callback, **kwargs)

    @overload
    def run(self) -> str: ...

    @overload
    def run(
        self, timeout: timedelta, injection_delay: timedelta, inject_func: Callable[..., Any]
    ) -> str: ...

    def run(
        self,
        timeout: timedelta | None = None,
        injection_delay: timedelta | None = None,
        inject_func: Callable[..., Any] | None = None,
    ) -> str:
        if injection_delay is None or inject_func is None:
            return self.__internal_injector.run(blocking=True)

        with concurrent.futures.ThreadPoolExecutor() as executor:
            event = self.__internal_injector.run(blocking=False)

            """
            This means that the event was triggered before the injection could take place.
            TODO: Maybe we should return the event instead of 'unknown'? Should this be an error?
            """
            if event != "unknown":
                print("Event triggered before injection")
                return event

            time.sleep(injection_delay.total_seconds())
            self.__internal_injector.interrupt()

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
        self.__internal_injector.close()

    def add_run(self, result: dict[str, Any], golden: bool = False) -> None:
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
            self.golden = result
        else:
            for key, value in result.items():
                print(f"{type(key)}: {value}")
                self.runs[key].append(value)

    ## TODO: Make a way better reporting function
    def report(self) -> None:
        print("Golden:")
        for key, value in self.golden.items():
            print(f"{key}: {value}")

        print("Runs:")
        for key, value in self.runs.items():
            for i, run in enumerate(value):
                print(f"{key} ({i}): {run}")

    def save(self, path: str) -> None:
        golden_path = path.split(".csv")[0] + "_golden.csv"

        if self.golden != {}:
            export_to_csv(golden_path, self.golden)

        if self.runs != {}:
            export_to_csv(path, self.runs)
