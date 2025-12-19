"""Field descriptor for describing environment schema fields."""

from typing import Any

# Sentinel used when no default value is provided.
_MISSING = object()


class Field:
    """Descriptor that defines a single environment schema field.

    Attributes:
        default: Default value (if the field is optional).
        env: Custom environment variable name.
        description: Optional description (for documentation).
        prefix: Prefix used for nested structures.
    """

    def __init__(
        self,
        default: Any = _MISSING,
        env: str | None = None,
        description: str | None = None,
        prefix: str | None = None,
    ) -> None:
        """Create a field descriptor.

        Args:
            default: Default value. If not provided, the field is required.
            env: Custom environment variable name.
            description: Field description (for documentation generation).
            prefix: Prefix for nested structures (for example, `"DB_"`).
        """
        self.default = default
        self.env = env
        self.description = description
        self.prefix = prefix
        self._name: Optional[str] = None

    def __set_name__(self, owner: type, name: str) -> None:
        """Called when the descriptor is assigned to a class attribute.

        Args:
            owner: Owning class.
            name: Attribute name on the class.
        """
        self._name = name

    @property
    def name(self) -> str:
        """Return the field name.

        Returns:
            Field name in the schema.

        Raises:
            RuntimeError: If the descriptor was not initialized properly.
        """
        if self._name is None:
            raise RuntimeError(
                "Field descriptor was not properly initialized. "
                "Make sure it's used as a class attribute."
            )
        return self._name

    def get_env_name(self, prefix: str = "") -> str:
        """Get the environment variable name for this field.

        Applies prefixes (if provided) and converts the field name to upper case.

        Args:
            prefix: Schema prefix (for nested structures).

        Returns:
            Environment variable name (upper case).
        """
        if self.env:
            # Кастомное имя — применяем только префикс схемы
            if prefix:
                return f"{prefix}{self.env}"
            return self.env

        env_name = self.name.upper()

        if self.prefix:
            env_name = f"{self.prefix}{env_name}"

        if prefix:
            env_name = f"{prefix}{env_name}"

        return env_name

    def has_default(self) -> bool:
        """Return whether the field has a default value.

        Returns:
            True if the field has a default value, False if it is required.
        """
        return self.default is not _MISSING

    def get_default(self) -> Any:
        """Return the default value.

        Returns:
            Default value.

        Raises:
            RuntimeError: If the field does not have a default value.
        """
        if not self.has_default():
            field_name = self._name or "<unnamed>"
            raise RuntimeError(f"Field '{field_name}' has no default value")
        return self.default

    def __repr__(self) -> str:
        """Return a debug representation of the descriptor.

        Returns:
            Debug string representation.
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
    """Create a `Field` from a simple default value.

    Used by the metaclass to turn plain defaults into `Field` descriptors.

    Args:
        default_value: Default value.

    Returns:
        A `Field` instance with the provided default.

    Example:
        >>> class Settings(EnvSchema):
        ...     debug: bool = False  # Automatically becomes Field(default=False)
    """
    return Field(default=default_value)
