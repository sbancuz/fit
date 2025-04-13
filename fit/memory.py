from typing import Union

from fit import logger
from fit.elf import ELF
from fit.interfaces.internal_injector import InternalInjector
from fit.mapping import Mapping

log = logger.get()


class IntList(list[int]):
    """
    Class that custom list for handling integer operations including bitwise and shift operators.
    """

    def __or__(self, other: Union[int, "IntList"]) -> list[int]:
        """
        Function that performs bitwise OR operation with an integer or another IntList.

        :param other: the integer or IntList to OR with.
        :return: the list of integers after performing the OR operation.
        """

        if isinstance(other, int):
            return list([x | other for x in self])
        elif isinstance(other, IntList):
            if len(other) != len(self):
                log.critical("IntList must have the same length")

            return [x | y for x, y in zip(self, other)]

    def __ror__(self, other: int) -> list[int]:
        """
        Function that perform bitwise OR operation with an integer.

        :param other: the integer to OR with.
        :return: the list of integers after performing the OR operation.
        """

        return list([other | x for x in self])

    def __xor__(self, other: Union[int, "IntList"]) -> list[int]:
        """
        Function that performs bitwise XOR operation with an integer or another IntList.

        :param other: the integer or IntList to XOR with.
        :return: the list of integers after performing the XOR operation.
        """

        if isinstance(other, int):
            return list([x ^ other for x in self])
        elif isinstance(other, IntList):
            if len(other) != len(self):
                log.critical("IntList must have the same length")

            return [x ^ y for x, y in zip(self, other)]

    def __rxor__(self, other: int) -> list[int]:
        """
        Function that performs bitwise XOR operation with an integer.

        :param other: the integer to XOR with.
        :return: the list of integers after performing the XOR operation.
        """

        return list([other ^ x for x in self])

    def __and__(self, other: Union[int, "IntList"]) -> list[int]:
        """
        Function that performs bitwise AND operation with an integer or another IntList.

        :param other: the integer or IntList to AND with.
        :return: the list of integers after performing the AND operation.
        """

        if isinstance(other, int):
            return list([x & other for x in self])
        elif isinstance(other, IntList):
            if len(other) != len(self):
                log.critical("IntList must have the same length")

            return [x & y for x, y in zip(self, other)]

    def __rand__(self, other: int) -> list[int]:
        """
        Function that performs bitwise AND operation with an integer.

        :param other: the integer to AND with.
        :return: the list of integers after performing the AND operation.
        """

        return list([other & x for x in self])

    def __lshift__(self, other: int) -> list[int]:
        """
        Function that performs bitwise << operation with an integer.

        :param other: the integer to << with.
        :return: the list of integers after performing the << operation.
        """

        return list([x << other for x in self])

    def __rshift__(self, other: int) -> list[int]:
        """
        Function that performs bitwise >> operation with an integer.

        :param other: the integer to >> with.
        :return: the list of integers after performing the >> operation.
        """

        return list([x >> other for x in self])


class Memory:
    """
    Class for managing memory operations using an internal injector.
    """

    """The internal injector instance."""
    __internal_injector: InternalInjector
    """The parsed ELF binary."""
    elf: ELF
    """The word size."""
    word_size: int

    @property
    def mappings(self) -> list[Mapping]:
        """
        Property that returns the memory mappings.

        :return: the list of memory mappings.
        """

        return self.__internal_injector.get_mappings()

    def __init__(self, injector: InternalInjector, elf: ELF) -> None:
        self.__internal_injector = injector
        self.elf = elf
        self.word_size = self.elf.bits // 8

    # @overload
    # def __getitem__(self, addr: int) -> int: ...

    # @overload
    # def __getitem__(self, addr: str) -> int: ...

    # @overload
    # def __getitem__(self, addr: slice) -> IntList: ...

    def __getitem__(self, addr: int | str | slice) -> int | IntList:
        """
        Function that get the value(s) at a specific memory address or range of addresses.

        :param addr: the memory address or range of addresses.
        :return: the value(s) at a specific memory address or range of addresses.
        """

        if isinstance(addr, str):
            """
            Support gdb-style symbols
            """

            location = addr
            offset = 0
            if location.count("+") == 1:
                location, off = location.split("+")

                if off.startswith("0x"):
                    offset = int(off, 16)
                else:
                    offset = int(off)

            elif location.count("-") == 1:
                location, off = location.split("-")

                if off.startswith("0x"):
                    offset = -int(off, 16)
                else:
                    offset = -int(off)

            start = self.elf.symbols[location].value + offset
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
            return self.__internal_injector.read_memory(start)

        return IntList(
            [
                self.__internal_injector.read_memory(true_addr)
                for true_addr in range(start, end, step)
            ]
        )

    # @overload
    # def __setitem__(self, addr: int, value: int) -> None: ...

    # @overload
    # def __setitem__(self, addr: str, value: int) -> None: ...

    # @overload
    # def __setitem__(self, addr: slice[int, int, int], value: int) -> None: ...

    # @overload
    # def __setitem__(self, addr: slice[int, int, int], value: list[int] | IntList) -> None: ...

    def __setitem__(self, addr: int | str | slice, value: int | list[int] | IntList) -> None:
        """
        Function that set the value(s) at a specific memory address or range of addresses.

        :param addr: the memory address or range of addresses.
        :param value: the value(s) to set.
        """

        if isinstance(addr, str):
            """
            Support gdb-style symbols
            """

            location = addr
            offset = 0
            if location.count("+") == 1:
                location, off = location.split("+")

                if off.startswith("0x"):
                    offset = int(off, 16)
                else:
                    offset = int(off)

            elif location.count("-") == 1:
                location, off = location.split("-")

                if off.startswith("0x"):
                    offset = -int(off, 16)
                else:
                    offset = -int(off)

            start = self.elf.symbols[location].value + offset
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
        """
        Function that returns the ranges of memory mappings.

        :return: the list of ranges of memory mappings.
        """

        return [mapping.as_range() for mapping in self.mappings]
