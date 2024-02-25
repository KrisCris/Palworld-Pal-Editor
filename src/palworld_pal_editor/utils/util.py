import re


def alphanumeric_key(key: str):
    """Converts a string into a list of integer and string fragments for sorting."""
    convert = lambda text: int(text) if text.isdigit() else text.lower()
    alphanumeric_list = [convert(c) for c in re.split("([0-9]+)", key)]
    return alphanumeric_list


def clamp(min_value: int, max_value: int, val: int) -> int:
    return max(min_value, min(max_value, val))
