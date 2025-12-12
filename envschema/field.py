"""Модуль дескриптора Field для описания полей схемы."""

from typing import Any

# Sentinel для отсутствия значения по умолчанию
_MISSING = object()


class Field:
    """Дескриптор для описания поля схемы окружения.

    Attributes:
        default: Значение по умолчанию (если не обязательное)
        env: Кастомное имя переменной окружения
        description: Описание поля для документации
        prefix: Префикс для вложенных структур
    """

    def __init__(
        self,
        default: Any = _MISSING,
        env: str | None = None,
        description: str | None = None,
        prefix: str | None = None,
    ) -> None:
        """Инициализирует дескриптор поля.

        Args:
            default: Значение по умолчанию. Если не указано, поле обязательное
            env: Кастомное имя переменной окружения
            description: Описание поля для автогенерации документации
            prefix: Префикс для вложенных структур (например, "DB_")
        """
        self.default = default
        self.env = env
        self.description = description
        self.prefix = prefix
        self._name: str | None = None

    def __set_name__(self, owner: type, name: str) -> None:
        """Вызывается при определении дескриптора в классе.

        Args:
            owner: Класс-владелец
            name: Имя атрибута в классе
        """
        self._name = name

    @property
    def name(self) -> str:
        """Возвращает имя поля.

        Returns:
            Имя поля в схеме

        Raises:
            RuntimeError: Если дескриптор не был правильно инициализирован
        """
        if self._name is None:
            raise RuntimeError(
                "Field descriptor was not properly initialized. "
                "Make sure it's used as a class attribute."
            )
        return self._name

    def get_env_name(self, prefix: str = "") -> str:
        """Получает имя переменной окружения для поля.

        Применяет префикс (если есть) и преобразует в UPPER_CASE.

        Args:
            prefix: Префикс схемы (если поле находится во вложенной структуре)

        Returns:
            Имя переменной окружения (UPPER_CASE)
        """
        if self.env:
            # Кастомное имя — применяем только префикс схемы
            if prefix:
                return f"{prefix}{self.env}"
            return self.env

        # Преобразуем имя поля в UPPER_CASE
        env_name = self.name.upper()

        # Добавляем префикс Field'а (для вложенных структур)
        if self.prefix:
            env_name = f"{self.prefix}{env_name}"

        # Добавляем префикс схемы
        if prefix:
            env_name = f"{prefix}{env_name}"

        return env_name

    def has_default(self) -> bool:
        """Проверяет, есть ли у поля значение по умолчанию.

        Returns:
            True если поле имеет значение по умолчанию, False если обязательное
        """
        return self.default is not _MISSING

    def get_default(self) -> Any:
        """Получает значение по умолчанию.

        Returns:
            Значение по умолчанию

        Raises:
            RuntimeError: Если поле не имеет значения по умолчанию
        """
        if not self.has_default():
            field_name = self._name or "<unnamed>"
            raise RuntimeError(f"Field '{field_name}' has no default value")
        return self.default

    def __repr__(self) -> str:
        """Возвращает строковое представление дескриптора.

        Returns:
            Строковое представление для отладки
        """
        parts = []

        if self.has_default():
            parts.append(f"default={self.default!r}")

        if self.env:
            parts.append(f"env={self.env!r}")

        if self.description:
            parts.append(f"description={self.description!r}")

        if self.prefix:
            parts.append(f"prefix={self.prefix!r}")

        args = ", ".join(parts) if parts else ""
        return f"Field({args})"


def field_from_default(default_value: Any) -> Field:
    """Создает Field из значения по умолчанию.

    Используется для автоматического создания Field'ов из простых дефолтов.

    Args:
        default_value: Значение по умолчанию

    Returns:
        Field с указанным значением по умолчанию

    Example:
        >>> class Settings(EnvSchema):
        ...     debug: bool = False  # Автоматически → Field(default=False)
    """
    return Field(default=default_value)
