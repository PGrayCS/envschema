from typing import Any


class ValidationError(Exception):
    """Ошибка валидации одного поля.

    Attributes:
        field_name: Имя поля в схеме
        env_var: Имя переменной окружения
        message: Описание ошибки
        value: Значение, которое не прошло валидацию (если есть)
        expected_type: Ожидаемый тип данных (если применимо)
    """

    def __init__(
        self,
        field_name: str,
        env_var: str,
        message: str,
        value: Any | None = None,
        expected_type: str | None = None,
    ) -> None:
        """Инициализирует ошибку валидации.

        Args:
            field_name: Имя поля в схеме
            env_var: Имя переменной окружения
            message: Описание ошибки
            value: Значение, которое не прошло валидацию
            expected_type: Ожидаемый тип данных
        """
        self.field_name = field_name
        self.env_var = env_var
        self.message = message
        self.value = value
        self.expected_type = expected_type
        super().__init__(message)

    def format(self) -> str:
        """Форматирует ошибку в читаемую строку.

        Returns:
            Отформатированное сообщение об ошибке
        """
        msg = f"{self.env_var}: {self.message}"

        if self.expected_type:
            msg += f" (expected type: {self.expected_type})"

        if self.value is not None:
            value_repr = repr(self.value)
            if len(value_repr) > 50:
                value_repr = value_repr[:47] + "..."
            msg += f" [got: {value_repr}]"

        return msg

    def __repr__(self) -> str:
        """Возвращает строковое представление ошибки.

        Returns:
            Строковое представление для отладки
        """
        return (
            f"ValidationError(field={self.field_name!r}, "
            f"env_var={self.env_var!r}, message={self.message!r})"
        )


class EnvSchemaError(Exception):
    """Исключение при загрузке и валидации схемы окружения.

    Агрегирует множественные ошибки валидации и форматирует их
    в понятное сообщение.

    Attributes:
        errors: Список ошибок валидации
    """

    def __init__(self, errors: list[ValidationError]) -> None:
        """Инициализирует исключение с набором ошибок.

        Args:
            errors: Список ошибок валидации
        """
        self.errors = errors
        message = self._format_errors()
        super().__init__(message)

    def _format_errors(self) -> str:
        """Форматирует все ошибки в единое сообщение.

        Returns:
            Отформатированное сообщение со всеми ошибками
        """
        if not self.errors:
            return "Unknown environment schema error"

        error_count = len(self.errors)
        plural = "s" if error_count > 1 else ""

        lines = [f"Failed to load environment variables ({error_count} error{plural}):"]

        for error in self.errors:
            lines.append(f"  * {error.format()}")

        return "\n".join(lines)

    def __repr__(self) -> str:
        """Возвращает строковое представление исключения.

        Returns:
            Строковое представление для отладки
        """
        return f"EnvSchemaError(errors={self.errors!r})"
