from typing import Callable
from datetime import timedelta

from fit.interfaces.injector import InternalInjector, Implementation

class Injector:

    __internal_injector: InternalInjector

    def __init__(self, elf: str, implementation: str = 'gdb', **kwargs) -> None:
        impl = Implementation.from_string(implementation)
        ## TODO: check for the right architecture and setup the regs
        self.__internal_injector = impl(elf, **kwargs)

    def reset(self) -> None:
        self.__internal_injector.reset()

    def set_timeout(self, timeout: timedelta) -> None:
        pass

    def set_result_condition(self, event: str, callback: Callable, **kwargs) -> None:
        self.__internal_injector.set_event(event, callback, **kwargs)

    ## TODO: Overload the [] operator to access memory
    ## TODO: Overload [start ... end] to access memory range
    ## TODO: Overload ['variable'] to access memory
    ## TODO: Overload | to write to memory
    ## TODO: Overload the other operators to error out
    memory: dict[int, int] = {}

    ## TODO: Overload the . operator to access registers
    ## TODO: Overload | to write to memory
    ## TODO: Overload the other operators to error out
    regs: dict[str, int] = {}
    
    def run(self) -> None:
        pass

    
            
