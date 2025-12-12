import pytest

from envschema.casters import (
    cast_bool,
    cast_dict,
    cast_float,
    cast_int,
    cast_list,
    cast_str,
    cast_value,
    register_caster,
)


class TestCastStr:
    """Тесты для cast_str."""

    def test_returns_string_as_is(self) -> None:
        """Проверяет, что строка возвращается без изменений."""
        assert cast_str("hello") == "hello"
        assert cast_str("123") == "123"
        assert cast_str("") == ""


class TestCastInt:
    """Тесты для cast_int."""

    def test_valid_integer(self) -> None:
        """Проверяет кастинг валидных целых чисел."""
        assert cast_int("123") == 123
        assert cast_int("0") == 0
        assert cast_int("-42") == -42

    def test_invalid_integer(self) -> None:
        """Проверяет ошибку при невалидном значении."""
        with pytest.raises(ValueError, match="cannot cast 'abc' to int"):
            cast_int("abc")

        with pytest.raises(ValueError, match="cannot cast '12.5' to int"):
            cast_int("12.5")


class TestCastFloat:
    """Тесты для cast_float."""

    def test_valid_float(self) -> None:
        """Проверяет кастинг валидных чисел с плавающей точкой."""
        assert cast_float("123.5") == 123.5
        assert cast_float("0.0") == 0.0
        assert cast_float("-42.7") == -42.7
        assert cast_float("123") == 123.0

    def test_invalid_float(self) -> None:
        """Проверяет ошибку при невалидном значении."""
        with pytest.raises(ValueError, match="cannot cast 'abc' to float"):
            cast_float("abc")


class TestCastBool:
    """Тесты для cast_bool."""

    def test_true_values(self) -> None:
        """Проверяет кастинг значений True."""
        assert cast_bool("true") is True
        assert cast_bool("True") is True
        assert cast_bool("TRUE") is True
        assert cast_bool("yes") is True
        assert cast_bool("YES") is True
        assert cast_bool("1") is True
        assert cast_bool("on") is True
        assert cast_bool("ON") is True

    def test_false_values(self) -> None:
        """Проверяет кастинг значений False."""
        assert cast_bool("false") is False
        assert cast_bool("False") is False
        assert cast_bool("FALSE") is False
        assert cast_bool("no") is False
        assert cast_bool("NO") is False
        assert cast_bool("0") is False
        assert cast_bool("off") is False
        assert cast_bool("OFF") is False

    def test_invalid_bool(self) -> None:
        """Проверяет ошибку при невалидном значении."""
        with pytest.raises(ValueError, match="invalid boolean value 'maybe'"):
            cast_bool("maybe")

        with pytest.raises(ValueError, match="invalid boolean value '2'"):
            cast_bool("2")


class TestCastList:
    """Тесты для cast_list."""

    def test_json_array_string_list(self) -> None:
        """Проверяет парсинг JSON массива строк."""
        result = cast_list('["a", "b", "c"]')
        assert result == ["a", "b", "c"]

    def test_json_array_int_list(self) -> None:
        """Проверяет парсинг JSON массива чисел."""
        result = cast_list("[1, 2, 3]", item_type=int)
        assert result == [1, 2, 3]

    def test_csv_string_list(self) -> None:
        """Проверяет парсинг CSV строки."""
        result = cast_list("a,b,c")
        assert result == ["a", "b", "c"]

    def test_csv_int_list(self) -> None:
        """Проверяет парсинг CSV строки с кастингом в int."""
        result = cast_list("1,2,3", item_type=int)
        assert result == [1, 2, 3]

    def test_empty_list(self) -> None:
        """Проверяет обработку пустого списка."""
        assert cast_list("") == []
        assert cast_list("[]") == []

    def test_invalid_json_array(self) -> None:
        """Проверяет ошибку при невалидном JSON."""
        with pytest.raises(ValueError, match="invalid JSON array"):
            cast_list("[invalid json]")

    def test_invalid_list_items(self) -> None:
        """Проверяет ошибку при невалидных элементах списка."""
        with pytest.raises(ValueError, match="cannot cast list items to int"):
            cast_list("1,abc,3", item_type=int)


class TestCastDict:
    """Тесты для cast_dict."""

    def test_valid_json_object(self) -> None:
        """Проверяет парсинг валидного JSON объекта."""
        result = cast_dict('{"key": "value", "num": 42}')
        assert result == {"key": "value", "num": 42}

    def test_invalid_json_object(self) -> None:
        """Проверяет ошибку при невалидном JSON."""
        with pytest.raises(ValueError, match="invalid JSON object"):
            cast_dict("{invalid json")

    def test_not_a_dict(self) -> None:
        """Проверяет ошибку, если JSON не объект."""
        with pytest.raises(ValueError, match="expected JSON object"):
            cast_dict('["array", "not", "object"]')


class TestCastValue:
    """Тесты для cast_value."""

    def test_basic_types(self) -> None:
        """Проверяет кастинг базовых типов."""
        assert cast_value("123", int) == 123
        assert cast_value("45.6", float) == 45.6
        assert cast_value("hello", str) == "hello"
        assert cast_value("true", bool) is True

    def test_list_type(self) -> None:
        """Проверяет кастинг списков."""
        result = cast_value("1,2,3", list[int])
        assert result == [1, 2, 3]

        result = cast_value('["a", "b"]', list[str])
        assert result == ["a", "b"]

    def test_unknown_type(self) -> None:
        """Проверяет ошибку для неизвестного типа."""
        with pytest.raises(ValueError, match="no caster registered"):
            cast_value("value", tuple)  # type: ignore[arg-type]


class TestRegisterCaster:
    """Тесты для register_caster."""

    def test_register_custom_caster(self) -> None:
        """Проверяет регистрацию кастомного кастера."""

        def cast_uppercase(value: str) -> str:
            return value.upper()

        register_caster(str, cast_uppercase)
        result = cast_value("hello", str)
        assert result == "HELLO"

        # Восстанавливаем оригинальный кастер
        from envschema.casters import cast_str

        register_caster(str, cast_str)
