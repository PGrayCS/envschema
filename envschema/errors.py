from typing import Any


class ValidationError:
    """Validation error for a single schema field.

    Attributes:
        field_name: Field name in the schema.
        env_var: Environment variable name.
        message: Human-readable error message.
        value: The offending value, if available.
        expected_type: Expected type name, if available.
    """

    def __init__(
        self,
        field_name: str,
        env_var: str,
        message: str,
        value: Any | None = None,
        expected_type: str | None = None,
    ) -> None:
        """Create a validation error.

        Args:
            field_name: Field name in the schema.
            env_var: Environment variable name.
            message: Human-readable error message.
            value: The offending value, if available.
            expected_type: Expected type name, if available.
        """
        self.field_name = field_name
        self.env_var = env_var
        self.message = message
        self.value = value
        self.expected_type = expected_type

    def format(self) -> str:
        """Format the error as a readable string.

        Returns:
            Formatted error message.
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
        """Return a debug representation of the error.

        Returns:
            Debug string representation.
        """
        return (
            f"ValidationError(field={self.field_name!r}, "
            f"env_var={self.env_var!r}, message={self.message!r})"
        )


class EnvSchemaError(Exception):
    """Raised when loading/validating an environment schema fails.

    Aggregates multiple validation errors into a single readable message.

    Attributes:
        errors: List of validation errors.
    """

    def __init__(self, errors: list[ValidationError]) -> None:
        """Create an exception with the given validation errors.

        Args:
            errors: List of validation errors.
        """
        self.errors = errors
        message = self._format_errors()
        super().__init__(message)

    def _format_errors(self) -> str:
        """Format all errors into a single message.

        Returns:
            A formatted message containing all errors.
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
        """Return a debug representation of the exception.

        Returns:
            Debug string representation.
        """
        return f"EnvSchemaError(errors={self.errors!r})"
