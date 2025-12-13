"""envschema - минималистичная библиотека для работы с переменными окружения.

Типобезопасная загрузка, кастинг и валидация environment variables
на основе аннотаций типов.

Пример использования:
    >>> from envschema import EnvSchema, Field
    >>>
    >>> class Settings(EnvSchema):
    ...     port: int
    ...     debug: bool = Field(default=False)
    ...     database_url: str = Field(env="DATABASE_URL")
    >>>
    >>> settings = Settings.load()
    >>> print(settings.port)
"""

from .casters import register_caster
from .errors import EnvSchemaError, ValidationError
from .field import Field
from .schema import EnvSchema

__version__ = "0.1.0"

__all__ = [
    "EnvSchema",
    "Field",
    "EnvSchemaError",
    "ValidationError",
    "register_caster",
]
