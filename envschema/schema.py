import os
from typing import Any, Optional, get_type_hints

from .errors import EnvSchemaError, ValidationError
from .field import Field, field_from_default, _MISSING
from .casters import cast_value


class EnvSchemaMeta(type):
    """Метакласс для EnvSchema.
    
    Обрабатывает аннотации типов и создает Field дескрипторы.
    """
    
    def __new__(
        mcs,
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, Any],
        **kwargs: Any
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
        if name == 'EnvSchema':
            return cls
        
        # Получаем аннотации типов
        annotations = namespace.get('__annotations__', {})
        
        # Обрабатываем каждое поле
        for field_name, field_type in annotations.items():
            # Проверяем, есть ли уже Field дескриптор
            field_value = namespace.get(field_name, _MISSING)
            
            if isinstance(field_value, Field):
                # Уже Field, оставляем как есть
                field_obj = field_value
            elif field_value is not _MISSING:
                # Простое значение по умолчанию → создаем Field
                field_obj = field_from_default(field_value)
                setattr(cls, field_name, field_obj)
            else:
                # Обязательное поле без значения → создаем Field без default
                field_obj = Field()
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
    def load(
        cls,
        env: Optional[dict[str, str]] = None,
        prefix: str = "",
    ) -> "EnvSchema":
        """Загружает и валидирует схему из переменных окружения.
        
        Args:
            env: Словарь переменных окружения (по умолчанию os.environ)
            prefix: Префикс для всех переменных схемы
            
        Returns:
            Экземпляр схемы со значениями из окружения
            
        Raises:
            EnvSchemaError: Если валидация не прошла
        """
        if env is None:
            env = dict(os.environ)
        
        fields = cls._get_fields()
        errors: list[ValidationError] = []
        values: dict[str, Any] = {}
        
        for field_name, (field, field_type) in fields.items():
            env_name = field.get_env_name(prefix)
            
            try:
                value = cls._load_field(
                    field=field,
                    field_name=field_name,
                    field_type=field_type,
                    env_name=env_name,
                    env=env,
                )
                values[field_name] = value
                
            except ValidationError as e:
                errors.append(e)
        
        if errors:
            raise EnvSchemaError(errors)
        
        return cls(**values)
    
    @classmethod
    def _load_field(
        cls,
        field: Field,
        field_name: str,
        field_type: type,
        env_name: str,
        env: dict[str, str],
    ) -> Any:
        """Загружает и валидирует одно поле.
        
        Args:
            field: Дескриптор поля
            field_name: Имя поля в схеме
            field_type: Тип поля
            env_name: Имя переменной окружения
            env: Словарь переменных окружения
            
        Returns:
            Значение поля
            
        Raises:
            ValidationError: Если валидация не прошла
        """
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
            )
    
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