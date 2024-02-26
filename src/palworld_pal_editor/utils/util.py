import re
from functools import wraps
from typing import Callable, get_type_hints


def alphanumeric_key(key: str):
    """Converts a string into a list of integer and string fragments for sorting."""
    convert = lambda text: int(text) if text.isdigit() else text.lower()
    alphanumeric_list = [convert(c) for c in re.split("([0-9]+)", key)]
    return alphanumeric_list


def clamp(min_value: int, max_value: int, val: int) -> int:
    return max(min_value, min(max_value, val))


def type_guard(func: Callable):
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Get type hints for the function
        hints = get_type_hints(func)
        
        # Check positional arguments
        for i, (arg, hint) in enumerate(zip(args, hints.values())):
            if not isinstance(arg, hint):
                raise TypeError(f"Argument {i+1} of {func.__name__} expected {hint}, got {type(arg)}")

        # Check keyword arguments
        for arg_name, arg_value in kwargs.items():
            if arg_name in hints and not isinstance(arg_value, hints[arg_name]):
                raise TypeError(f"Argument '{arg_name}' of {func.__name__} expected {hints[arg_name]}, got {type(arg_value)}")

        return func(*args, **kwargs)

    return wrapper
