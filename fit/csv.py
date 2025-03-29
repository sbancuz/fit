import csv
from typing import Any


def import_from_csv(file_path: str) -> dict[str, Any]:
    """
    Reads a CSV file and returns a dictionary.
    - Column headers become keys.
    - Values are stored as lists.
    """
    result: dict[str, list[Any]] = {}
    with open(file_path, mode="r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            for key, value in row.items():
                if key not in result:
                    result[key] = []
                result[key].append(value)
    return result


import csv
from typing import Any


def export_to_csv(file_path: str, data: dict[str, Any], result: list[Any]) -> None:
    """
    Saves a dictionary to a CSV file.
    - Keys become column headers.
    - Values can be single values or lists.
    - If a value is a list, it expands into multiple rows.
    - If 'result' is provided, adds a 'result' column as the first column.
    """

    for value in data.values():
        if isinstance(value, dict):
            raise ValueError("Nested dictionaries are not allowed")

    max_length = max((len(v) if isinstance(v, list) else 1) for v in data.values())

    if result:
        if len(result) != max_length:
            raise ValueError("Length of result list must match the longest data list")

    normalized_data = {
        key: (value if isinstance(value, list) else [value] * max_length)
        for key, value in data.items()
    }

    fieldnames = ["result"] if result else []
    fieldnames.extend(data.keys())

    with open(file_path, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for i in range(max_length):
            row = {key: normalized_data[key][i] for key in data}
            if result:
                row["result"] = result[i]
            writer.writerow(row)
