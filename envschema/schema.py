import os
from typing import Any, Optional, get_type_hints

from .errors import EnvSchemaError, ValidationError
from .field import Field, field_from_default, _MISSING
from .casters import cast_value


class EnvSchemaMeta(type):
    """Metaclass for `EnvSchema`.

    Processes type annotations and creates `Field` descriptors.
    """
    
    def __new__(
        mcs,
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, Any],
        **kwargs: Any
    ) -> type:
        """Create a new schema class.

        Args:
            name: Class name.
            bases: Base classes.
            namespace: Class namespace.
            **kwargs: Additional arguments passed to the metaclass.

        Returns:
            Newly created schema class.
        """
        cls = super().__new__(mcs, name, bases, namespace, **kwargs)

        if name == 'EnvSchema':
            return cls

        annotations = namespace.get('__annotations__', {})

        for field_name, field_type in annotations.items():
            field_value = namespace.get(field_name, _MISSING)

            if isinstance(field_value, Field):
                field_obj = field_value
            elif field_value is not _MISSING:
                field_obj = field_from_default(field_value)
                setattr(cls, field_name, field_obj)
            else:
                field_obj = Field()
                setattr(cls, field_name, field_obj)

        return cls


class EnvSchema(metaclass=EnvSchemaMeta):
    """Base class for environment variable schemas.

    Example:
        >>> class Settings(EnvSchema):
        ...     port: int
        ...     debug: bool = False
        ...     api_key: str = Field(env="SECRET_API_KEY")
        >>> settings = Settings.load()
    """
    
    def __init__(self, **values: Any) -> None:
        """Initialize the schema instance with field values.

        Args:
            **values: Field values.
        """
        for key, value in values.items():
            setattr(self, key, value)
    
    @classmethod
    def _get_fields(cls) -> dict[str, tuple[Field, type]]:
        """Return all schema fields with their types.

        Returns:
            Mapping of field name to `(Field, type)`.
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
        """Load and validate the schema from environment variables.

        Args:
            env: Environment variables mapping (defaults to `os.environ`).
            prefix: Prefix applied to all schema variables.

        Returns:
            Schema instance populated from environment variables.

        Raises:
            EnvSchemaError: If validation fails.
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
        """Load and validate a single field.

        Args:
            field: Field descriptor.
            field_name: Field name in the schema.
            field_type: Field type.
            env_name: Environment variable name.
            env: Environment variables mapping.

        Returns:
            Parsed field value.

        Raises:
            ValidationError: If validation fails.
        """
        raw_value = env.get(env_name)

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
        """Return a debug representation of the schema instance.

        Returns:
            Debug string representation.
        """
        fields = self._get_fields()
        field_values = []

        for field_name in fields.keys():
            value = getattr(self, field_name, None)
            field_values.append(f"{field_name}={value!r}")

        fields_str = ", ".join(field_values)
        return f"{self.__class__.__name__}({fields_str})"
