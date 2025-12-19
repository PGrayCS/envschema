import json
from collections.abc import Callable
from typing import Any, TypeVar, Union, cast, get_args, get_origin

T = TypeVar("T")
CasterFunc = Callable[[str], Any]


def cast_str(value: str) -> str:
    """Return the value as a string.

    Args:
        value: Raw string value from the environment.

    Returns:
        The original value unchanged.
    """
    return value


def cast_int(value: str) -> int:
    """Cast the value to an integer.

    Args:
        value: Raw string value from the environment.

    Returns:
        Parsed integer value.

    Raises:
        ValueError: If the value cannot be converted to `int`.
    """
    try:
        return int(value)
    except ValueError:
        raise ValueError(f"cannot cast '{value}' to int") from None


def cast_float(value: str) -> float:
    """Cast the value to a float.

    Args:
        value: Raw string value from the environment.

    Returns:
        Parsed float value.

    Raises:
        ValueError: If the value cannot be converted to `float`.
    """
    try:
        return float(value)
    except ValueError:
        raise ValueError(f"cannot cast '{value}' to float") from None


def cast_bool(value: str) -> bool:
    """Cast the value to a boolean.

    Supported values (case-insensitive):
    - True: "true", "yes", "1", "on"
    - False: "false", "no", "0", "off"

    Args:
        value: Raw string value from the environment.

    Returns:
        Parsed boolean value.

    Raises:
        ValueError: If the value cannot be interpreted as a boolean.
    """
    normalized = value.lower().strip()

    if normalized in ("true", "yes", "1", "on"):
        return True
    elif normalized in ("false", "no", "0", "off"):
        return False
    else:
        raise ValueError(
            f"invalid boolean value '{value}' (expected: true/false/yes/no/1/0/on/off)"
        )


def cast_list(value: str, item_type: type = str) -> list:
    """Cast the value to a list.

    The input format is detected automatically:
    - If the string looks like a JSON array, it is parsed as JSON.
    - Otherwise, it is parsed as comma-separated values.

    Args:
        value: Raw string value from the environment.
        item_type: Element type for the list (defaults to `str`).

    Returns:
        A list of parsed elements.

    Raises:
        ValueError: If the value cannot be parsed.
    """
    stripped = value.strip()

    if stripped.startswith('[') and stripped.endswith(']'):
        try:
            parsed = json.loads(stripped)
            if not isinstance(parsed, list):
                raise ValueError(f"expected JSON array, got {type(parsed)}")

            if item_type != str:
                caster = _get_caster_for_type(item_type)
                return [caster(str(item)) for item in parsed]
            return parsed

        except json.JSONDecodeError as e:
            raise ValueError(f"invalid JSON array: {e}")

    if not stripped:
        return []

    items = [item.strip() for item in stripped.split(',')]

    if item_type != str:
        caster = _get_caster_for_type(item_type)
        try:
            return [caster(item) for item in items]
        except ValueError as e:
            raise ValueError(
                f"cannot cast list items to {_get_type_name(item_type)}: {e}"
            ) from e

    return items


def cast_dict(value: str) -> dict:
    """Cast the value to a dictionary using JSON.

    Args:
        value: Raw string value from the environment (JSON format).

    Returns:
        Parsed dictionary.

    Raises:
        ValueError: If the value cannot be parsed as a JSON object.
    """
    try:
        parsed = json.loads(value)
        if not isinstance(parsed, dict):
            raise ValueError(f"expected JSON object, got {type(parsed).__name__}")
        return parsed
    except json.JSONDecodeError as e:
        raise ValueError(f"invalid JSON object: {e}") from e


# Registry of caster functions for built-in types.
_CASTERS: dict[type, CasterFunc] = {
    str: cast_str,
    int: cast_int,
    float: cast_float,
    bool: cast_bool,
    dict: cast_dict,
}


def register_caster(type_: type, caster: CasterFunc) -> None:
    """Register a custom caster function for a type.

    Args:
        type_: Target type.
        caster: Caster function (`str -> type_`).

    Example:
        >>> def cast_timedelta(value: str) -> timedelta:
        ...     return timedelta(seconds=int(value))
        >>> register_caster(timedelta, cast_timedelta)
    """
    _CASTERS[type_] = caster


def _get_caster_for_type(type_: type) -> CasterFunc:
    """Get the caster function registered for a given type.

    Args:
        type_: Target type.

    Returns:
        A caster function.

    Raises:
        ValueError: If no caster is registered for the given type.
    """
    if type_ in _CASTERS:
        return _CASTERS[type_]

    raise ValueError(f"no caster registered for type {type_}")


def is_optional_type(type_: type) -> bool:
    """Проверяет, является ли тип Optional[T] или Union[T, None].

    Args:
        type_: Тип для проверки

    Returns:
        True если тип является Optional[T] или Union[T, None]
    """
    origin = get_origin(type_)

    # Проверяем, является ли origin Union-типом
    # В Python 3.10+ это types.UnionType для X | Y синтаксиса
    # или typing.Union для Union[X, Y]
    if origin is Union:
        args = get_args(type_)
        # Union должен содержать ровно 2 аргумента, один из которых NoneType
        return len(args) == 2 and type(None) in args

    # Проверяем новый синтаксис Python 3.10+ (X | Y)
    try:
        import types

        if hasattr(types, "UnionType") and isinstance(type_, types.UnionType):
            args = get_args(type_)
            return len(args) == 2 and type(None) in args
    except (ImportError, AttributeError):
        pass

    return False


def get_optional_inner_type(type_: type) -> type:
    """Извлекает внутренний тип T из Optional[T].

    Args:
        type_: Optional тип

    Returns:
        Внутренний тип T

    Raises:
        ValueError: Если тип не является Optional
    """
    if not is_optional_type(type_):
        raise ValueError(f"type {type_} is not Optional")

    args = get_args(type_)

    # Возвращаем тип, который не NoneType
    for arg in args:
        if arg is not type(None):
            # Явно приводим к type, так как get_args может вернуть Any
            return cast(type, arg)

    raise ValueError(f"cannot extract inner type from {type_}")


def _get_type_name(type_: type) -> str:
    """Безопасно получает имя типа для отображения.

    Обрабатывает все случаи, включая UnionType, Optional, list[T] и т.д.

    Args:
        type_: Тип данных

    Returns:
        Строковое представление имени типа
    """
    if is_optional_type(type_):
        inner_type = get_optional_inner_type(type_)
        inner_name = _get_type_name(inner_type)
        return f"Optional[{inner_name}]"

    origin = get_origin(type_)
    if origin is list:
        args = get_args(type_)
        item_type = args[0] if args else str
        item_name = _get_type_name(item_type)
        return f"list[{item_name}]"

    return getattr(type_, "__name__", str(type_))


def cast_value(value: str, type_: type) -> Any:
    """Cast the value to the given type.

    Supports built-in types and `list[T]`.

    Args:
        value: Raw string value from the environment.
        type_: Target type.

    Returns:
        The parsed value.

    Raises:
        ValueError: If casting is not possible.
    """
    if is_optional_type(type_):
        inner_type = get_optional_inner_type(type_)
        return cast_value(value, inner_type)

    origin = get_origin(type_)

    if origin is list:
        args = get_args(type_)
        item_type = args[0] if args else str
        return cast_list(value, item_type)

    caster = _get_caster_for_type(type_)
    return caster(value)
