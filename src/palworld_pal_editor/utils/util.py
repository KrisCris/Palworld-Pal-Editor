import re
from functools import wraps
import sys
from typing import Callable, Optional, get_type_hints, Union, _GenericAlias

from palworld_pal_editor.utils import LOGGER

def alphanumeric_key(key: str):
    """Converts a string into a list of integer and string fragments for sorting."""
    convert = lambda text: int(text) if text.isdigit() else text.lower()
    alphanumeric_list = [convert(c) for c in re.split("([0-9]+)", key)]
    return alphanumeric_list


def clamp(min_value: int, max_value: int, val: int) -> int:
    return max(min_value, min(max_value, val))


def is_union_type(hint):
    import types
    return isinstance(hint, types.UnionType)


def is_instance(obj, hint):
    if is_union_type(hint):
        return any(is_instance(obj, sub_hint) for sub_hint in getattr(hint, '__args__', []))
    else:
        return isinstance(obj, hint)


def convert_type(value, to_type):
    if is_union_type(to_type):
        for sub_type in getattr(to_type, '__args__', []):
            try:
                return sub_type(value)
            except (ValueError, TypeError):
                continue
        raise TypeError(f"Cannot convert value '{value}' to any of {to_type}")
    else:
        try:
            return to_type(value)
        except (ValueError, TypeError) as e:
            raise TypeError(f"Cannot convert value '{value}' of type {type(value).__name__} to {to_type.__name__}") from e


def type_guard(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        hints = get_type_hints(func)
        arg_names = func.__code__.co_varnames[:func.__code__.co_argcount]
        all_args = dict(zip(arg_names, args))
        all_args.update(kwargs)

        for arg_name, arg_value in all_args.items():
            hint = hints.get(arg_name)
            if hint and not is_instance(arg_value, hint):
                try:
                    all_args[arg_name] = convert_type(arg_value, hint)
                except TypeError as e:
                    LOGGER.warning(f"Argument '{arg_name}' of {func.__name__} expected {hint}, got {type(arg_value).__name__}. Error: {e}")
                    raise e  # Raise the error instead of returning TypeError
        return func(**all_args)

    return wrapper