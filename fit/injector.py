from typing import Callable, overload, Sequence
from datetime import timedelta

import concurrent.futures
import time

from fit.elf import ELF
from fit.interfaces.internal_injector import InternalInjector
from fit.interfaces.implementations import Implementation

class Memory:

    class IntList(list[int]):
        """
        This class has to be used as an intermediary to allow |= like operations on lists of integers.
        They are defined as element-wise operations.
        """
        def __or__(self, other: int) -> list[int]:
            return list([x | other for x in self])

        def __xor__(self, other: int) -> list[int]:
            return list([x ^ other for x in self])

        def __and__(self, other: int) -> list[int]:
            return list([x & other for x in self])

        def __lshift__(self, other: int) -> list[int]:
            return list([x << other for x in self])

        def __rshift__(self, other: int) -> list[int]:
            return list([x >> other for x in self])

    __internal_injector: InternalInjector

    elf: ELF

    word_size: int

    def __init__(self, injector: InternalInjector, elf: ELF) -> None:
        self.__internal_injector = injector
        self.elf = elf
        self.word_size = self.elf.bits // 8

    @overload
    def __getitem__(self, addr: int) -> int:
        ...

    @overload
    def __getitem__(self, addr: str) -> int:
        ...

    @overload
    def __getitem__(self, addr: slice) -> IntList:
        ...

    def __getitem__(self, addr: int | str | slice) -> int | IntList:
        if isinstance(addr, str):
            start = self.elf.symbols[addr].value
            step = self.word_size
            end = start + step
        elif isinstance(addr, int):
            start = addr
            step = self.word_size
            end = start + step
        elif isinstance(addr, slice):
            # Use addr.start, addr.stop, addr.step (with defaults if needed)
            start = addr.start if addr.start is not None else 0
            if addr.stop is None:
                raise ValueError("Slice stop must be specified")

            end = addr.stop
            step = addr.step if addr.step is not None else self.word_size

        if step == self.word_size:
            return self.__internal_injector.read_memory(start, self.word_size)

        return Memory.IntList([self.__internal_injector.read_memory(true_addr, self.word_size)
                for true_addr in range(start, end, step)])

    @overload
    def __setitem__(self, addr: int, value: int) -> None:
        ...

    @overload
    def __setitem__(self, addr: str, value: int) -> None:
        ...

    @overload
    def __setitem__(self, addr: slice, value: int) -> None:
        ...

    @overload
    def __setitem__(self, addr: slice, value: list[int]) -> None:
        ...

    def __setitem__(self, addr: int | str | slice, value: int | list[int]) -> None:
        if isinstance(addr, str):
            start = self.elf.symbols[addr].value
            step = self.word_size 
            end = start + step
        elif isinstance(addr, int):
            start = addr
            step = self.word_size
            end = start + step
        elif isinstance(addr, slice):
            # Use addr.start, addr.stop, addr.step (with defaults if needed)
            start = addr.start if addr.start is not None else 0
            if addr.stop is None:
                raise ValueError("Slice stop must be specified")

            end = addr.stop
            step = addr.step if addr.step is not None else self.word_size

        if isinstance(value, int):
            for true_addr in range(start, end, step):
                self.__internal_injector.write_memory(true_addr, value)
        elif isinstance(value, list):
            for true_addr, val in zip(range(start, end, step), value):
                self.__internal_injector.write_memory(true_addr, val)

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

    timeout: timedelta | None = None

    events: dict[str, Callable] = {}

    binary: ELF 

    memory: Memory

    regs: Registers

    def __init__(self, bin: str, implementation: str = 'gdb', **kwargs) -> None:
        impl = Implementation.from_string(implementation)
        ## TODO: check for the right architecture and setup the regs
        self.__internal_injector = impl(bin, **kwargs)
        self.binary = ELF(bin)

        self.regs = Registers(self.__internal_injector, self.binary)
        self.memory = Memory(self.__internal_injector, self.binary)

    def reset(self) -> None:
        self.__internal_injector.reset()

    def set_timeout(self, timeout: timedelta) -> None:
        self.timeout = timeout

    def set_result_condition(self, event: str, callback: Callable, **kwargs) -> None:
        self.__internal_injector.set_event(event, callback, **kwargs)

        self.events[event] = callback

    @overload
    def run(self) -> str:
        ...

    @overload
    def run(self, delay: timedelta, inject_func: Callable) -> str:
        ...

    def run(self, delay: timedelta | None = None, inject_func: Callable | None = None) -> str:
        if delay is None or inject_func is None:
            return self.__internal_injector.run()

        with concurrent.futures.ThreadPoolExecutor() as executor:

            event = self.__internal_injector.run()

            """
            This means that the event was triggered before the injection could take place.
            TODO: Maybe we should return the event instead of 'unknown'? Should this be an error?
            """
            if event != 'unknown':
                return event

            time.sleep(delay.total_seconds())
            self.__internal_injector.interrupt()

            inject_func(self)

            proc = executor.submit(self.__internal_injector.run)

            try:
                if self.timeout is None:
                    return proc.result()
                
                return proc.result(timeout=self.timeout.total_seconds())
            except concurrent.futures.TimeoutError:
                return 'Timeout'

    def close(self) -> None:
        self.__internal_injector.close()
            
