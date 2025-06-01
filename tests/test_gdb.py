import platform

from fit.interfaces.gdb.gdb_injector import get_int, parse_memory


def test_gdb_value_parsing() -> None:
    assert get_int("abcdefab", "little") == 0xABEFCDAB
    assert get_int("abcdefab", "big") == 0xABCDEFAB


def test_gdb_memory_parsing() -> None:
    val = [
        {
            "begin": "0x0000000000404010",
            "offset": "0x0000000000000000",
            "end": "0x0000000000404014",
            "contents": "ffffffff",
        }
    ]

    assert parse_memory(val, 4, 8, "little")[0] == 0xFFFFFFFF

    val = [
        {
            "begin": "0x000000000040403c",
            "offset": "0x0000000000000000",
            "end": "0x0000000000404048",
            "contents": "010000000200000003000000",
        }
    ]

    if platform.architecture()[0] == "64bit":
        assert parse_memory(val, 12, 8, "little") == [0x2_00000001, 3]
    else:
        assert parse_memory(val, 12, 8, "little") == [0x1, 2, 3]
