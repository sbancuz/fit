from typing import overload

from fit.elf import ELF
from fit.interfaces.internal_injector import InternalInjector
from fit.mapping import Mapping


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


class Memory:
    __internal_injector: InternalInjector

    elf: ELF

    word_size: int

    @property
    def mappings(self) -> list[Mapping]:
        return self.__internal_injector.get_mappings()

    def __init__(self, injector: InternalInjector, elf: ELF) -> None:
        self.__internal_injector = injector
        self.elf = elf
        self.word_size = self.elf.bits // 8

    @overload
    def __getitem__(self, addr: int) -> int: ...

    @overload
    def __getitem__(self, addr: str) -> int: ...

    @overload
    def __getitem__(self, addr: slice) -> IntList: ...

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

        return IntList(
            [
                self.__internal_injector.read_memory(true_addr, self.word_size)
                for true_addr in range(start, end, step)
            ]
        )

    @overload
    def __setitem__(self, addr: int, value: int) -> None: ...

    @overload
    def __setitem__(self, addr: str, value: int) -> None: ...

    @overload
    def __setitem__(self, addr: slice, value: int) -> None: ...

    @overload
    def __setitem__(self, addr: slice, value: list[int] | IntList) -> None: ...

    def __setitem__(self, addr: int | str | slice, value: int | list[int] | IntList) -> None:
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
        else:
            if isinstance(value, IntList):
                value = list(value)

            for true_addr, val in zip(range(start, end, step), value):
                self.__internal_injector.write_memory(true_addr, val)

    def mapping_ranges(self) -> list[range]:
        return [mapping.as_range() for mapping in self.mappings]
