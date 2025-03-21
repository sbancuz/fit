import enum
from typing import Type

from fit.interfaces.gdb.gdb_injector import GDBInjector
from fit.interfaces.internal_injector import InternalInjector


class Implementation(enum.Enum):
    GDB = 1

    @classmethod
    def from_string(cls, s: str) -> Type["InternalInjector"]:
        if s.lower() == "gdb":
            return GDBInjector.get_class()
        else:
            raise ValueError(f"Unknown implementation: {s}")
