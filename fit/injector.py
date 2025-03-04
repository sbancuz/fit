import concurrent.futures
import time
from datetime import timedelta
from typing import Any, Callable, overload

from fit.elf import ELF
from fit.interfaces.implementations import Implementation
from fit.interfaces.internal_injector import InternalInjector
from fit.memory import Memory


def noop() -> None:
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

    def __init__(
        self,
        bin: str,
        implementation: str = "gdb",
        **kwargs: Any,
    ) -> None:
        impl = Implementation.from_string(implementation)
        ## TODO: check for the right architecture and setup the regs
        self.__internal_injector = impl(bin, **kwargs)
        self.binary = ELF(bin)

        self.regs = Registers(self.__internal_injector, self.binary)
        self.memory = Memory(self.__internal_injector, self.binary)

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
