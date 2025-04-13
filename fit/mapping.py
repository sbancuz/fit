class Mapping:
    """
    Class representing a memory mapping.
    """

    """The starting address of the memory mapping."""
    start: int
    """The ending address of the memory mapping."""
    end: int
    """The size of the memory mapping."""
    size: int
    """The offset of the memory mapping in the file."""
    offset: int
    """The permissions of the memory mapping."""
    permissions: int
    """The file associated with the memory mapping."""
    file: str

    class Permissions:
        """
        Class representing the permissions of the file.
        """

        READ = 1
        WRITE = 2
        EXEC = 4
        PRIVATE = 8

    def __init__(
        self, start: int, end: int, size: int, offset: int, permission: int, file: str
    ) -> None:
        self.start = start
        self.end = end
        self.size = size
        self.offset = offset
        self.permissions = permission
        self.file = file

    def __repr__(self) -> str:
        """
        Function that returns the string representation of the memory mapping.

        :return: the string representation of the memory mapping.
        """

        perm = "r" if self.permissions & Mapping.Permissions.READ == 1 else "-"
        perm += "w" if self.permissions & Mapping.Permissions.WRITE == 2 else "-"
        perm += "x" if self.permissions & Mapping.Permissions.EXEC == 4 else "-"
        perm += "p" if self.permissions & Mapping.Permissions.PRIVATE == 8 else "-"

        return (
            f"Mapping(start={hex(self.start)},"
            + f"end={hex(self.end)}, size={hex(self.size)},"
            + f" offset={hex(self.offset)}, {perm}, {self.file})"
        )

    @property
    def is_readable(self) -> bool:
        """
        Property that checks if the mapping is readable.

        :return: True if the mapping is readable, False otherwise.
        """

        return self.permissions & Mapping.Permissions.READ == 1

    @property
    def is_writable(self) -> bool:
        """
        Property that checks if the mapping is writable.

        :return: True if the mapping is writable, False otherwise.
        """

        return self.permissions & Mapping.Permissions.WRITE == 2

    @property
    def is_executable(self) -> bool:
        """
        Property that checks if the mapping is executable.

        :return: True if the mapping is executable, False otherwise.
        """

        return self.permissions & Mapping.Permissions.EXEC == 4

    @property
    def is_private(self) -> bool:
        """
        Property that checks if the mapping is private.

        :return: True if the mapping is private, False otherwise.
        """

        return self.permissions & Mapping.Permissions.PRIVATE == 8

    def as_range(self) -> range:
        """
        Function that returns the range of the memory mapping.

        :return: the memory mapping range.
        """

        return range(self.start, self.end)
