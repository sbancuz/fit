from fit.injector import Injector


def gdb_injector(
    bin: str,
    gdb_path: str = "gdb_multiarch",
    remote: str | None = None,
    embedded: bool = True,
    board_family: str | None = None,
) -> Injector:
    kwargs = {
        "gdb_path": gdb_path,
        "embedded": embedded,
    }
    if remote is not None:
        kwargs["remote"] = remote

    if embedded and board_family is not None:
        kwargs["board_family"] = board_family

    return Injector(bin, "gdb", **kwargs)
