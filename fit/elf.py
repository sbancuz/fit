import lief

import fit.logger

log = fit.logger.get(__name__)


class ELF:
    __bin: lief.ELF.Binary

    def __init__(self, path: str) -> None:
        self.__bin = lief.parse(path)
        if self.__bin is None:
            log.critical(f"Failed to parse ELF binary at {path}")

        self.symbols = ELF.Symbols(self.__bin)
        self.sections = ELF.Sections(self.__bin)

    class Symbols:
        def __init__(self, bin: lief.ELF.Binary) -> None:
            self.__bin = bin

        def __getitem__(self, name: str) -> lief.Symbol:
            return self.__bin.get_symbol(name)

    class Sections:
        def __init__(self, bin: lief.ELF.Binary) -> None:
            self.__bin = bin

        def __getitem__(self, name: str) -> lief.Section:
            return self.__bin.get_section(name)

    symbols: Symbols

    sections: Sections

    @property
    def architecture(self) -> lief.ELF.ARCH:
        return self.__bin.header.machine_type

    @property
    def bits(self) -> int:
        return 64 if self.__bin.header.identity_class == lief.ELF.Header.CLASS.ELF64 else 32

    @property
    def header(self) -> lief.ELF.Header:
        return self.__bin.header

    @property
    def segments(self) -> lief.ELF.Binary.it_segments:
        return self.__bin.segments

    @property
    def lief(self) -> lief.ELF.Binary:
        return self.__bin
