import csv
import sys
from typing import Any


def import_from_csv(file_path: str) -> dict[str, Any]:
    """
    Function that imports data from a CSV file and stores it in a dictionary.

    Each key in the dictionary corresponds to a column header and the value is a list of entries in that column.

    :param file_path: the path to the CSV file to be imported.
    :return: the dictionary containing the CSV data, where each key is a column header and the value is a list of column entries.
    """
    csv.field_size_limit(sys.maxsize)
    result: dict[str, list[Any]] = {}
    with open(file_path, mode="r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            for key, value in row.items():
                if key not in result:
                    result[key] = []
                result[key].append(value)
    return result


def export_to_csv(file_path: str, data: dict[str, Any]) -> None:
    """
    Function that exports data from a dictionary to a CSV file.

    Each key in the dictionary corresponds to a column header and the value is a list of entries in that column.
    The function raises a ValueError if any value in the dictionary is a nested dictionary.
    It normalizes the data to ensure all columns have the same number of entries by repeating single values to match the longest list.

    :param file_path: The path to the CSV file to be created.
    :param data: A dictionary containing the data to be exported, where each key is a column header.
    :raises ValueError: If any value in the dictionary is a nested dictionary.
    """

    for value in data.values():
        if isinstance(value, dict):
            raise ValueError("Nested dictionaries are not allowed")

    max_length = max((len(v) if isinstance(v, list) else 1) for v in data.values())

    normalized_data = {
        key: (value if isinstance(value, list) else [value] * max_length)
        for key, value in data.items()
    }

    with open(file_path, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=data.keys())
        writer.writeheader()
        for i in range(max_length):
            row = {key: normalized_data[key][i] for key in data}
            writer.writerow(row)
