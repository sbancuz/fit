from fit.injector import Injector


def gdb_injector(
    bin: str,
    gdb_path: str = "gdb_multiarch",
    remote: str | None = None,
    embeded: bool = True,
) -> Injector:
    kwargs = {
        "gdb_path": gdb_path,
        "embeded": embeded,
    }
    if remote is not None:
        kwargs["remote"] = remote

    return Injector(bin, "gdb", **kwargs)
