import json
from collections.abc import Callable
from typing import Any, TypeVar, Union, cast, get_args, get_origin

T = TypeVar("T")
CasterFunc = Callable[[str], Any]


def cast_str(value: str) -> str:
    """Кастит значение в строку.

    Args:
        value: Строковое значение из окружения

    Returns:
        Исходная строка без изменений
    """
    return value


def cast_int(value: str) -> int:
    """Кастит значение в целое число.

    Args:
        value: Строковое значение из окружения

    Returns:
        Целое число

    Raises:
        ValueError: Если значение невозможно преобразовать в int
    """
    try:
        return int(value)
    except ValueError:
        raise ValueError(f"cannot cast '{value}' to int") from None


def cast_float(value: str) -> float:
    """Кастит значение в число с плавающей точкой.

    Args:
        value: Строковое значение из окружения

    Returns:
        Число с плавающей точкой

    Raises:
        ValueError: Если значение невозможно преобразовать в float
    """
    try:
        return float(value)
    except ValueError:
        raise ValueError(f"cannot cast '{value}' to float") from None


def cast_bool(value: str) -> bool:
    """Кастит значение в булево значение.

    Поддерживаемые значения:
    - True: "true", "yes", "1", "on" (регистронезависимо)
    - False: "false", "no", "0", "off" (регистронезависимо)

    Args:
        value: Строковое значение из окружения

    Returns:
        Булево значение

    Raises:
        ValueError: Если значение не распознано как bool
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
    """Кастит значение в список.

    Автоматически определяет формат:
    - Если строка выглядит как JSON массив → парсит как JSON
    - Иначе → парсит как CSV (разделитель: запятая)

    Args:
        value: Строковое значение из окружения
        item_type: Тип элементов списка (по умолчанию str)

    Returns:
        Список элементов указанного типа

    Raises:
        ValueError: Если значение невозможно распарсить
    """
    stripped = value.strip()

    # Проверяем, выглядит ли как JSON массив
    if stripped.startswith("[") and stripped.endswith("]"):
        try:
            parsed = json.loads(stripped)
            if not isinstance(parsed, list):
                raise ValueError(f"expected JSON array, got {type(parsed)}")

            # Кастим элементы в нужный тип
            if item_type is not str:
                caster = _get_caster_for_type(item_type)
                return [caster(str(item)) for item in parsed]
            return parsed

        except json.JSONDecodeError as e:
            raise ValueError(f"invalid JSON array: {e}") from e

    # Парсим как CSV
    if not stripped:
        return []

    items = [item.strip() for item in stripped.split(",")]

    # Кастим элементы в нужный тип
    if item_type is not str:
        caster = _get_caster_for_type(item_type)
        try:
            return [caster(item) for item in items]
        except ValueError as e:
            raise ValueError(
                f"cannot cast list items to {_get_type_name(item_type)}: {e}"
            ) from e

    return items


def cast_dict(value: str) -> dict:
    """Кастит значение в словарь через JSON.

    Args:
        value: Строковое значение из окружения (JSON формат)

    Returns:
        Словарь

    Raises:
        ValueError: Если значение невозможно распарсить как JSON объект
    """
    try:
        parsed = json.loads(value)
        if not isinstance(parsed, dict):
            raise ValueError(f"expected JSON object, got {type(parsed).__name__}")
        return parsed
    except json.JSONDecodeError as e:
        raise ValueError(f"invalid JSON object: {e}") from e


# Реестр кастеров для базовых типов
_CASTERS: dict[type, CasterFunc] = {
    str: cast_str,
    int: cast_int,
    float: cast_float,
    bool: cast_bool,
    dict: cast_dict,
}


def register_caster(type_: type, caster: CasterFunc) -> None:
    """Регистрирует кастомный кастер для типа.

    Args:
        type_: Тип данных
        caster: Функция кастинга (str -> type_)

    Example:
        >>> def cast_timedelta(value: str) -> timedelta:
        ...     return timedelta(seconds=int(value))
        >>> register_caster(timedelta, cast_timedelta)
    """
    _CASTERS[type_] = caster


def _get_caster_for_type(type_: type) -> CasterFunc:
    """Получает функцию кастинга для типа.

    Args:
        type_: Тип данных

    Returns:
        Функция кастинга

    Raises:
        ValueError: Если кастер для типа не найден
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
    # Для Optional[T] показываем как Optional[inner_type]
    if is_optional_type(type_):
        inner_type = get_optional_inner_type(type_)
        inner_name = _get_type_name(inner_type)
        return f"Optional[{inner_name}]"

    # Для list[T] показываем как list[item_type]
    origin = get_origin(type_)
    if origin is list:
        args = get_args(type_)
        item_type = args[0] if args else str
        item_name = _get_type_name(item_type)
        return f"list[{item_name}]"

    # Для обычных типов используем __name__ или str()
    return getattr(type_, "__name__", str(type_))


def cast_value(value: str, type_: type) -> Any:
    """Кастит значение в указанный тип.

    Поддерживает базовые типы, list[T] и Optional[T].

    Args:
        value: Строковое значение из окружения
        type_: Целевой тип данных

    Returns:
        Значение указанного типа

    Raises:
        ValueError: Если кастинг невозможен
    """
    # Обработка Optional[T] - должна быть первой
    if is_optional_type(type_):
        inner_type = get_optional_inner_type(type_)
        return cast_value(value, inner_type)

    origin = get_origin(type_)

    # Обработка list[T]
    if origin is list:
        args = get_args(type_)
        item_type = args[0] if args else str
        return cast_list(value, item_type)

    # Обработка базовых типов
    caster = _get_caster_for_type(type_)
    return caster(value)
