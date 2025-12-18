from pathlib import Path
from typing import Any, get_type_hints

from .casters import cast_value
from .errors import EnvSchemaError, ValidationError
from .field import _MISSING, Field, field_from_default
from .loader import load_env_with_dotenv


class EnvSchemaMeta(type):
    """Метакласс для EnvSchema.

    Обрабатывает аннотации типов и создает Field дескрипторы.
    """

    def __new__(
        mcs,
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, Any],
        **kwargs: Any,
    ) -> type:
        """Создает новый класс схемы.

        Args:
            name: Имя класса
            bases: Базовые классы
            namespace: Пространство имен класса
            **kwargs: Дополнительные аргументы

        Returns:
            Новый класс схемы
        """
        cls = super().__new__(mcs, name, bases, namespace, **kwargs)

        # Не обрабатываем базовый класс EnvSchema
        if name == "EnvSchema":
            return cls

        # Получаем аннотации типов
        annotations = namespace.get("__annotations__", {})

        # Обрабатываем каждое поле
        for field_name, _field_type in annotations.items():
            # Проверяем, есть ли уже Field дескриптор
            field_value = namespace.get(field_name, _MISSING)

            if isinstance(field_value, Field):
                # Уже Field — вызываем __set_name__ если не был вызван
                field_value.__set_name__(cls, field_name)
            elif field_value is not _MISSING:
                # Простое значение по умолчанию → создаем Field
                field_obj = field_from_default(field_value)
                field_obj.__set_name__(cls, field_name)
                setattr(cls, field_name, field_obj)
            else:
                # Обязательное поле без значения → создаем Field без default
                field_obj = Field()
                field_obj.__set_name__(cls, field_name)
                setattr(cls, field_name, field_obj)

        return cls


class EnvSchema(metaclass=EnvSchemaMeta):
    """Базовый класс для схем переменных окружения.

    Пример использования:
        >>> class Settings(EnvSchema):
        ...     port: int
        ...     debug: bool = False
        ...     api_key: str = Field(env="SECRET_API_KEY")
        >>> settings = Settings.load()
    """

    def __init__(self, **values: Any) -> None:
        """Инициализирует экземпляр схемы с значениями.

        Args:
            **values: Значения полей
        """
        for key, value in values.items():
            setattr(self, key, value)

    @classmethod
    def _get_fields(cls) -> dict[str, tuple[Field, type]]:
        """Получает все поля схемы с их типами.

        Returns:
            Словарь {имя_поля: (Field, тип)}
        """
        fields = {}
        type_hints = get_type_hints(cls)

        for attr_name in dir(cls):
            attr_value = getattr(cls, attr_name)

            if isinstance(attr_value, Field):
                field_type = type_hints.get(attr_name, str)
                fields[attr_name] = (attr_value, field_type)

        return fields

    @classmethod
    def _is_nested_schema(cls, field_type: type) -> bool:
        """Проверяет, является ли тип вложенной схемой.

        Args:
            field_type: Тип поля

        Returns:
            True если тип является подклассом EnvSchema
        """
        try:
            return isinstance(field_type, type) and issubclass(field_type, EnvSchema)
        except TypeError:
            return False

    @classmethod
    def load(
        cls,
        env: dict[str, str] | None = None,
        prefix: str = "",
        dotenv_path: str | Path | bool | None = None,
        dotenv_override: bool = False,
    ) -> "EnvSchema":
        """Загружает и валидирует схему из переменных окружения.

        Args:
            env: Словарь переменных окружения (по умолчанию os.environ)
            prefix: Префикс для всех переменных схемы
            dotenv_path: Путь к .env файлу, True для автопоиска, None для игнора
            dotenv_override: Если True, .env перезаписывает системные переменные

        Raises:
            EnvSchemaError: Если валидация не прошла
            ImportError: Если python-dotenv не установлен (if using dotenv_path)
            FileNotFoundError: Если .env файл не найден

        Example:
            >>> settings = Settings.load()  # Только os.environ
            >>> settings = Settings.load(dotenv_path=".env")  # С .env файлом
            >>> settings = Settings.load(dotenv_path=True)  # Автопоиск .env
        """
        if env is None:
            # Загружаем окружение с поддержкой .env файлов
            env = load_env_with_dotenv(dotenv_path, dotenv_override)

        fields = cls._get_fields()
        errors: list[ValidationError] = []
        values: dict[str, Any] = {}

        for field_name, (field, field_type) in fields.items():
            try:
                value = cls._load_field(
                    field=field,
                    field_name=field_name,
                    field_type=field_type,
                    parent_prefix=prefix,
                    env=env,
                )
                values[field_name] = value

            except ValidationError as e:
                errors.append(e)
            except EnvSchemaError as e:
                # Агрегируем ошибки из вложенных схем
                errors.extend(e.errors)

        if errors:
            raise EnvSchemaError(errors)

        return cls(**values)

    @classmethod
    def _compute_nested_prefix(
        cls, field: Field, field_name: str, parent_prefix: str
    ) -> str:
        """Вычисляет префикс для вложенной схемы.

        Args:
            field: Дескриптор поля
            field_name: Имя поля в схеме
            parent_prefix: Префикс родительской схемы

        Returns:
            Полный префикс для вложенной схемы
        """
        # Если указан кастомный префикс в Field(prefix="...")
        if field.prefix is not None:
            nested_prefix = field.prefix
        else:
            # Используем имя поля в UPPER_CASE + "_"
            nested_prefix = f"{field_name.upper()}_"

        # Добавляем родительский префикс
        if parent_prefix:
            return f"{parent_prefix}{nested_prefix}"

        return nested_prefix

    @classmethod
    def _load_field(
        cls,
        field: Field,
        field_name: str,
        field_type: type,
        parent_prefix: str,
        env: dict[str, str],
    ) -> Any:
        """Загружает и валидирует одно поле.

        Args:
            field: Дескриптор поля
            field_name: Имя поля в схеме
            field_type: Тип поля
            parent_prefix: Префикс родительской схемы
            env: Словарь переменных окружения

        Returns:
            Значение поля

        Raises:
            ValidationError: Если валидация не прошла
            EnvSchemaError: Если валидация вложенной схемы не прошла
        """
        # Проверяем, является ли поле вложенной схемой
        if cls._is_nested_schema(field_type):
            return cls._load_nested_schema(
                field=field,
                field_name=field_name,
                schema_type=field_type,
                parent_prefix=parent_prefix,
                env=env,
            )

        # Обычное поле
        env_name = field.get_env_name(parent_prefix)
        raw_value = env.get(env_name)

        # Проверяем наличие значения
        if raw_value is None:
            if field.has_default():
                return field.get_default()
            else:
                raise ValidationError(
                    field_name=field_name,
                    env_var=env_name,
                    message="missing required environment variable",
                    expected_type=field_type.__name__,
                )

        # Кастим значение в нужный тип
        try:
            return cast_value(raw_value, field_type)
        except ValueError as e:
            raise ValidationError(
                field_name=field_name,
                env_var=env_name,
                message=str(e),
                value=raw_value,
                expected_type=field_type.__name__,
            ) from e

    @classmethod
    def _load_nested_schema(
        cls,
        field: Field,
        field_name: str,
        schema_type: type["EnvSchema"],
        parent_prefix: str,
        env: dict[str, str],
    ) -> "EnvSchema":
        """Загружает вложенную схему.

        Args:
            field: Дескриптор поля
            field_name: Имя поля в схеме
            schema_type: Тип вложенной схемы
            parent_prefix: Префикс родительской схемы
            env: Словарь переменных окружения

        Returns:
            Экземпляр вложенной схемы

        Raises:
            EnvSchemaError: Если валидация вложенной схемы не прошла
        """
        nested_prefix = cls._compute_nested_prefix(field, field_name, parent_prefix)

        # Рекурсивно загружаем вложенную схему
        # EnvSchemaError пробросится наверх для агрегации ошибок
        return schema_type.load(env=env, prefix=nested_prefix)

    def __repr__(self) -> str:
        """Возвращает строковое представление схемы.

        Returns:
            Строковое представление для отладки
        """
        fields = self._get_fields()
        field_values = []

        for field_name in fields.keys():
            value = getattr(self, field_name, None)
            field_values.append(f"{field_name}={value!r}")

        fields_str = ", ".join(field_values)
        return f"{self.__class__.__name__}({fields_str})"
