from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable, Self, Type

from fit.mapping import Mapping


class InternalInjector(ABC):
    """
    Abstract class for managing the injection process into an ELF binary.
    """

    @classmethod
    def get_class(cls) -> Type[Self]:  # Ensures correct subclass return type
        """
        Function that returns the class type.

        :return: the class type.
        """

        return cls  # Returns the class itself

    @abstractmethod
    def __init__(self: InternalInjector, elf_path: str, **kwargs: dict[str, Any]) -> None:
        """Constructor method."""

    @abstractmethod
    def reset(self: InternalInjector) -> None:
        """
        Function that resets the injector to a known initial state. Useful between test runs or injections.
        """

    @abstractmethod
    def set_event(self: InternalInjector, event: str) -> None:
        """
        Function that sets a specific event for this target.

        :param event: the event to set.
        """

    @abstractmethod
    def read_memory(self: InternalInjector, address: int, count: int) -> list[int]:
        """
        Function that reads a memory word from the target.

        :param address: the memory address to read from.
        :param count: the number of bytes to read.
        :return: the values read from the target.
        """

    @abstractmethod
    def write_memory(self: InternalInjector, address: int, value: list[int], repeat: int) -> None:
        """
        Function that writes a memory word from the target.

        :param address: the memory address to write to.
        :param value: the value to write.
        :param repeat: the number of times to write the value.
        """

    @abstractmethod
    def read_register(self: InternalInjector, register: str) -> int:
        """
        Function that reads a register from the target.

        :param register: the register to read.
        :return: the value read from the target.
        """

    @abstractmethod
    def write_register(self: InternalInjector, register: str, value: int) -> None:
        """
        Function that writes a register from the target.

        :param register: the register to write.
        :param value: the value to write.
        """

    @abstractmethod
    def close(self: InternalInjector) -> None:
        """
        Function that closes the GDB session and exit the controller.
        """

    @abstractmethod
    def run(self: InternalInjector, blocking: bool = True) -> str:
        """
        Function that runs the injector for a given amount of time.

        :param blocking: whether to block until the precess stops.
        :return: the name of the breakpoint hit.
        """

    @abstractmethod
    def get_register_names(self: InternalInjector) -> list[str]: ...

    """
    Function that returns a list of registers names.
    
    :return: the list of registers names.
    """

    @abstractmethod
    def is_running(self: InternalInjector) -> bool: ...

    """
    Function that checks if the target is running.
    
    :return: True if the target is running.
    """

    @abstractmethod
    def interrupt(self: InternalInjector) -> str | None: ...

    """
    Function that interrupts the running process.
    """

    @abstractmethod
    def get_mappings(self: InternalInjector) -> list[Mapping]: ...

    """
    Function that retrieves memory mappings using GDB's 'info proc mappings'
    
    :return: the list of memory mappings. 
    """
