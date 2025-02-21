from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Callable, Type, Self

import enum

from fit.interfaces.gdb.gdb_injector import GDBIjector

class Implementation(enum.Enum):
    GDB = 1

    @classmethod
    def from_string(cls, s: str) -> Type['InternalInjector']:
        if s.lower() == 'gdb':
            return GDBIjector.get_class()
        else:
            raise ValueError(f'Unknown implementation: {s}')

class InternalInjector(ABC):

    @classmethod
    def get_class(cls) -> Type[Self]:  # Ensures correct subclass return type
        return cls  # Returns the class itself

    @abstractmethod
    def __init__(self: InternalInjector, elf_path: str,  **kwargs) -> None:
        """Constructor method."""

    @abstractmethod
    def reset(self: InternalInjector) -> None:
        """Reset the injector to its initial state."""

    @abstractmethod
    def set_event(self: InternalInjector, event: str, callback: Callable, **kwargs) -> None:
        """Set a handler for an event."""

    @abstractmethod
    def read_memory(self: InternalInjector, address: int) -> int:
        """Access memory at a given address."""

    @abstractmethod
    def write_memory(self: InternalInjector, address: int, value: int) -> None:
        """Write a value to memory at a given address."""

    @abstractmethod
    def read_register(self: InternalInjector, register: str) -> int:
        """Read the value of a register."""

    @abstractmethod
    def write_register(self: InternalInjector, register: str, value: int) -> None:
        """Write a value to a register."""

