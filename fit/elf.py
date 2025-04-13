from typing import cast

import lief

import fit.logger

log = fit.logger.get()


class ELF:
    """
    Class for parsing and interacting with ELF - Executable and Linkable Format - binaries.
    """

    """The path to the ELF binary file."""
    __bin: lief.ELF.Binary

    def __init__(self, path: str) -> None:
        bin = lief.parse(path)
        if bin is None:
            log.critical(f"Failed to parse ELF binary at {path}")
            return

        self.__bin = cast(lief.ELF.Binary, bin)

        self.symbols = ELF.Symbols(self.__bin)
        self.sections = ELF.Sections(self.__bin)

    class Symbols:
        """
        Class for parsing and interacting with ELF symbols.
        """

        def __init__(self, bin: lief.ELF.Binary) -> None:
            self.__bin = bin

        def __getitem__(self, name: str) -> lief.Symbol:
            """
            Gets a symbol by its name.

            :param name: the name of the symbol.
            :return: the symbol with the specified name.
            """

            return self.__bin.get_symbol(name)

    class Sections:
        """
        Class for parsing and interacting with ELF sections.
        """

        def __init__(self, bin: lief.ELF.Binary) -> None:
            self.__bin = bin

        def __getitem__(self, name: str) -> lief.Section:
            """
            Gets a section by its name.

            :param name: the name of the section.
            :return: the section with the specified name.
            """

            return self.__bin.get_section(name)

    """The ELF symbols."""
    symbols: Symbols
    """The ELF sections."""
    sections: Sections

    @property
    def architecture(self) -> lief.ELF.ARCH:
        """
        Property that returns the architecture of the ELF binary.

        :return: The architecture of the ELF binary.
        """

        return self.__bin.header.machine_type

    @property
    def bits(self) -> int:
        """
        Property that returns the bitness (32 or 64 bits) of the ELF binary.

        :return: 64 if the binary is 64-bit, otherwise 32.
        """

        return 64 if self.__bin.header.identity_class == lief.ELF.Header.CLASS.ELF64 else 32

    @property
    def header(self) -> lief.ELF.Header:
        """
        Property that returns the header of the ELF binary.

        :return: the header of the ELF binary.
        """

        return self.__bin.header

    @property
    def segments(self) -> lief.ELF.Binary.it_segments:
        """
        Property that returns the segments of the ELF binary.

        :return: the segments of the ELF binary.
        """

        return self.__bin.segments

    @property
    def lief(self) -> lief.ELF.Binary:
        """
        Property that returns the parsed ELF binary.

        :return: the parsed ELF binary.
        """

        return self.__bin
