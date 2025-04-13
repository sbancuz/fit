from fit.injector import Injector


def gdb_injector(
    bin: str,
    gdb_path: str = "gdb_multiarch",
    remote: str | None = None,
    embedded: bool = True,
    board_family: str | None = None,
) -> Injector:
    """
    Function that creates an Injector instance for GDB with optional parameters.

    :param bin: the path to the binary to be injected.
    :param gdb_path: the path to the GDB executable. Default is "gdb_multiarch".
    :param remote: the remote target for GDB. Default is None.
    :param embedded: the flag that indicates if the target is embedded. Default is True.
    :param board_family: the family of the embedded board, if applicable. Default is None.
    :return: the instance of Injector configured for GDB.
    """

    kwargs = {
        "gdb_path": gdb_path,
        "embedded": embedded,
    }

    if remote is not None:
        kwargs["remote"] = remote

    if embedded and board_family is not None:
        kwargs["board_family"] = board_family

    return Injector(bin, "gdb", **kwargs)
