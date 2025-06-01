import os
import platform
from datetime import timedelta

from fit import logger
from fit.elf import ELF
from fit.fitlib import gdb_injector
from fit.injector import Injector

dir_path = os.path.dirname(os.path.realpath(__file__))
log = logger.get()


def test_read_write() -> None:
    # This is an elf, it's just the makefile being weird
    # log.setLevel("DEBUG")
    bin_path = dir_path + "/out/testbench/read_write.c"

    inj = gdb_injector(
        bin=bin_path,
        gdb_path="gdb",
        embedded=False,
    )

    elf = ELF(bin_path)

    def read_write(inj: Injector) -> None:
        assert inj.memory["vmax1"] == 0xFFFFFFFF, "Read wrong value from injector"
        assert inj.memory["vzero1"] == 0, "Read wrong value from injector"

        vamx1_addr = elf.symbols["vmax1"].value

        if platform.architecture()[0] == "64bit":
            assert inj.memory[vamx1_addr : vamx1_addr + 12] == [0xFFFFFFFF_FFFFFFFF, 0xFFFFFFFF]
        else:
            assert inj.memory[vamx1_addr : vamx1_addr + 12] == [0xFFFFFFFF, 0xFFFFFFFF, 0xFFFFFFFF]

        inj.memory["vmax1"] ^= 0xFF
        assert inj.memory["vmax1"] == 0xFFFFFF00
        inj.memory["vmax2"] >>= 16
        assert inj.memory["vmax2"] == 0xFFFF
        inj.memory["vmax2"] <<= 16
        assert inj.memory["vmax2"] == 0xFFFF0000
        inj.memory["vmax3"] &= 0xF
        assert inj.memory["vmax3"] == 0xF

        inj.memory["vzero1"] = 0xF
        assert inj.memory["vzero1"] == 0xF
        inj.memory["vzero2"] |= 0xF
        assert inj.memory["vzero2"] == 0xF

        vzero3_addr = elf.symbols["vzero3"].value
        inj.memory[vzero3_addr : vzero3_addr + 12] = [0x2_00000001, 3]
        assert inj.memory["vzero3"] == 1
        assert inj.memory["vzero3+4"] == 2
        assert inj.memory["vzero3+8"] == 3
        assert inj.memory[vzero3_addr : vzero3_addr + 12] == [0x2_00000001, 3]

        vmax4_addr = elf.symbols["vmax5"].value
        inj.memory[vmax4_addr : vmax4_addr + 12] ^= 0xF
        assert inj.memory["vmax5"] == 0xFFFFFFF0
        if platform.architecture()[0] == "64bit":
            assert inj.memory["vmax5+4"] == 0xFFFFFFFF
        else:
            assert inj.memory["vmax5+4"] == 0xFFFFFFF0
        assert inj.memory["vmax5+8"] == 0xFFFFFFF0

    inj.reset()
    inj.set_result_condition("stop", read_write)

    assert inj.run() == "stop"


def test_timeout() -> None:
    # This is an elf, it's just the makefile being weird
    log.setLevel("DEBUG")
    bin_path = dir_path + "/out/testbench/timeout.c"

    inj = gdb_injector(
        bin=bin_path,
        gdb_path="gdb",
        embedded=False,
    )

    inj.reset()
    inj.set_result_condition("stop")

    assert (
        inj.run(
            timeout=timedelta(milliseconds=50),
        )
        == "Timeout"
    )


test_timeout()
