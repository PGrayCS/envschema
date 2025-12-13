"""envschema — a minimal library for working with environment variables.

Provides type-safe loading, casting, and validation of environment variables
based on Python type annotations.

Example:
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

from .schema import EnvSchema
from .field import Field
from .errors import EnvSchemaError, ValidationError
from .casters import register_caster

__version__ = "0.1.0"

__all__ = [
    "EnvSchema",
    "Field",
    "EnvSchemaError",
    "ValidationError",
    "register_caster",
]