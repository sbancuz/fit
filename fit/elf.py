import lief


class ELF:
    __bin: lief.ELF.Binary

    symbols: "ELF.Symbols"

    def __init__(self, path: str) -> None:
        self.__bin = lief.parse(path)
        assert self.__bin is not None

        self.symbols = ELF.Symbols(self.__bin)

    class Symbols:
        def __init__(self, bin: lief.ELF.Binary) -> None:
            self.__bin = bin

        def __getitem__(self, name: str) -> lief.Symbol:
            return self.__bin.get_symbol(name)

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
    def lief(self) -> lief.ELF.Binary:
        return self.__bin
