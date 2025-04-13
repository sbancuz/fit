import enum
from typing import Type

from fit.interfaces.gdb.gdb_injector import GDBInjector
from fit.interfaces.internal_injector import InternalInjector


class Implementation(enum.Enum):
    """
    Enumeration class for the available injector implementations.
    """

    GDB = 1

    @classmethod
    def from_string(cls, s: str) -> Type["InternalInjector"]:
        """
        Function that returns the injector class corresponding to a given implementation name.

        :param s: the implementation name.
        :return: the class corresponding to the given implementation name.
        """

        if s.lower() == "gdb":
            return GDBInjector.get_class()
        else:
            raise ValueError(f"Unknown implementation: {s}")
