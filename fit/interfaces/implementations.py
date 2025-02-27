from typing import Type

import enum

from fit.interfaces.gdb.gdb_injector import GDBIjector
from fit.interfaces.internal_injector import InternalInjector


class Implementation(enum.Enum):
    GDB = 1

    @classmethod
    def from_string(cls, s: str) -> Type["InternalInjector"]:
        if s.lower() == "gdb":
            return GDBIjector.get_class()
        else:
            raise ValueError(f"Unknown implementation: {s}")
