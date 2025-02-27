class Mapping:
    start: int 
    end: int 
    size: int 
    offset: int 
    permissions: int
    file: str

    class Permissions:
        READ = 1
        WRITE = 2
        EXEC = 4
        PRIVATE = 8

    def __init__(self, start: int, end: int, size: int, offset: int, permission: int, file: str) -> None:
        self.start = start
        self.end = end
        self.size = size
        self.offset = offset
        self.permissions = permission
        self.file = file

    def __repr__(self) -> str:
        perm  = 'r' if self.permissions & Mapping.Permissions.READ == 1 else '-'
        perm += 'w' if self.permissions & Mapping.Permissions.WRITE == 2 else '-'
        perm += 'x' if self.permissions & Mapping.Permissions.EXEC == 4 else '-'
        perm += 'p' if self.permissions & Mapping.Permissions.PRIVATE == 8 else '-'

        return f"Mapping(start={hex(self.start)}, end={hex(self.end)}, size={hex(self.size)}, offset={hex(self.offset)}, {perm}, {self.file})"

    @property
    def is_readable(self) -> bool:
            return self.permissions & Mapping.Permissions.READ == 1

    @property
    def is_writable(self) -> bool:
        return self.permissions & Mapping.Permissions.WRITE == 2

    @property
    def is_executable(self) -> bool:
        return self.permissions & Mapping.Permissions.EXEC == 4

    @property
    def is_private(self) -> bool:
        return self.permissions & Mapping.Permissions.PRIVATE == 8

    def as_range(self) -> range:
        return range(self.start, self.end)
