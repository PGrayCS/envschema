"""Модуль для генерации документации из схем EnvSchema."""

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any, get_args, get_origin

from .schema import EnvSchema


class TypeHandler:
    """Обработчик для конкретного типа данных.

    Attributes:
        format_default: Функция форматирования значения по умолчанию
        get_example: Функция генерации примера значения
        type_name: Имя типа для документации
    """

    def __init__(
        self,
        format_default: Callable[[Any], str],
        get_example: Callable[[], str],
        type_name: str | None = None,
    ) -> None:
        """Инициализирует обработчик типа.

        Args:
            format_default: Функция форматирования дефолтного значения
            get_example: Функция генерации примера
            type_name: Имя типа (если None, берется из type.__name__)
        """
        self.format_default = format_default
        self.get_example = get_example
        self.type_name = type_name


# Реестр обработчиков типов
TYPE_HANDLERS: dict[type, TypeHandler] = {
    str: TypeHandler(
        format_default=str,
        get_example=lambda: "your_value_here",
        type_name="str",
    ),
    int: TypeHandler(
        format_default=str,
        get_example=lambda: "0",
        type_name="int",
    ),
    float: TypeHandler(
        format_default=str,
        get_example=lambda: "0.0",
        type_name="float",
    ),
    bool: TypeHandler(
        format_default=lambda v: str(v).lower(),
        get_example=lambda: "true",
        type_name="bool",
    ),
    dict: TypeHandler(
        format_default=json.dumps,
        get_example=lambda: '{"key": "value"}',
        type_name="dict",
    ),
}


class DocumentationGenerator:
    """Генератор документации для EnvSchema.

    Attributes:
        schema_class: Класс схемы EnvSchema
        prefix: Префикс для переменных окружения
    """

    def __init__(
        self,
        schema_class: type[EnvSchema],
        prefix: str | None = None,
    ) -> None:
        """Инициализирует генератор.

        Args:
            schema_class: Класс схемы EnvSchema
            prefix: Префикс для переменных окружения (по умолчанию "")
        """
        self.schema_class = schema_class
        self.prefix = prefix or ""
        self._metadata_cache: list[dict[str, Any]] | None = None

    def _collect_metadata(self) -> list[dict[str, Any]]:
        """Собирает метаданные полей схемы.

        Returns:
            Список словарей с метаданными каждого поля
        """
        fields = self.schema_class._get_fields()
        metadata = []

        for field_name, (field, field_type) in fields.items():
            env_name = field.get_env_name(self.prefix)
            is_required = not field.has_default()
            default_value = field.get_default() if field.has_default() else None
            description = field.description or ""

            metadata.append(
                {
                    "field_name": field_name,
                    "env_name": env_name,
                    "field_type": field_type,
                    "is_required": is_required,
                    "default_value": default_value,
                    "description": description,
                }
            )

        return metadata

    def _get_field_metadata(self) -> list[dict[str, Any]]:
        """Получает метаданные полей (с кешированием).

        Returns:
            Список словарей с метаданными каждого поля
        """
        if self._metadata_cache is None:
            self._metadata_cache = self._collect_metadata()
        return self._metadata_cache

    def _get_handler_for_type(self, field_type: type) -> TypeHandler:
        """Получает обработчик для типа данных.

        Args:
            field_type: Тип поля

        Returns:
            Обработчик типа
        """
        origin = get_origin(field_type)

        # Обработка list[T]
        if origin is list:
            args = get_args(field_type)
            item_type = args[0] if args else str

            if item_type is str:
                # list[str] - CSV формат
                return TypeHandler(
                    format_default=lambda v: ",".join(str(item) for item in v),
                    get_example=lambda: "value1,value2",
                    type_name=f"list[{item_type.__name__}]",
                )
            else:
                # list[int], list[float] и т.д. - JSON массив
                return TypeHandler(
                    format_default=json.dumps,
                    get_example=lambda: "[1, 2, 3]",
                    type_name=f"list[{item_type.__name__}]",
                )

        # Базовые типы
        if field_type in TYPE_HANDLERS:
            return TYPE_HANDLERS[field_type]

        # Неизвестный тип - используем str как fallback
        return TypeHandler(
            format_default=str,
            get_example=lambda: "your_value_here",
            type_name=getattr(field_type, "__name__", str(field_type)),
        )

    def _format_default_value(self, value: Any, field_type: type) -> str:
        """Форматирует значение по умолчанию для .env файла.

        Args:
            value: Значение по умолчанию
            field_type: Тип поля

        Returns:
            Отформатированное строковое значение
        """
        if value is None:
            return ""

        handler = self._get_handler_for_type(field_type)
        return handler.format_default(value)

    def _get_example_value(self, field_type: type) -> str:
        """Получает пример значения для обязательного поля.

        Args:
            field_type: Тип поля

        Returns:
            Пример значения
        """
        handler = self._get_handler_for_type(field_type)
        return handler.get_example()

    def _format_type_name(self, field_type: type) -> str:
        """Форматирует имя типа для документации.

        Args:
            field_type: Тип поля

        Returns:
            Строковое представление типа
        """
        handler = self._get_handler_for_type(field_type)
        if handler.type_name:
            return handler.type_name

        type_name = getattr(field_type, "__name__", str(field_type))
        return str(type_name)

    def _escape_markdown(self, text: str) -> str:
        """Экранирует специальные символы Markdown.

        Args:
            text: Текст для экранирования

        Returns:
            Экранированный текст
        """
        if not text:
            return ""

        # Экранируем специальные символы Markdown
        replacements = [
            ("\\", "\\\\"),  # Сначала экранируем обратный слэш
            ("|", "\\|"),  # Таблицы
            ("_", "\\_"),  # Курсив/жирный
            ("*", "\\*"),  # Курсив/жирный
            ("[", "\\["),  # Ссылки
            ("]", "\\]"),  # Ссылки
            ("`", "\\`"),  # Код
        ]

        for old, new in replacements:
            text = text.replace(old, new)

        return text

    def generate_example_env(self, path: str | None = None) -> str:
        """Генерирует .env.example файл.

        Args:
            path: Путь к файлу для записи. Если None, возвращает строку

        Returns:
            Содержимое .env.example файла
        """
        metadata = self._get_field_metadata()
        lines = []

        for field_info in metadata:
            env_name = field_info["env_name"]
            description = field_info["description"]
            is_required = field_info["is_required"]
            default_value = field_info["default_value"]
            field_type = field_info["field_type"]

            # Формируем комментарий
            comment_parts = []
            if description:
                comment_parts.append(description)

            if not is_required and default_value is not None:
                formatted_default = self._format_default_value(
                    default_value, field_type
                )
                comment_parts.append(f"default: {formatted_default}")

            if is_required:
                comment_parts.append("required")

            # Добавляем комментарий
            if comment_parts:
                comment = " ".join(comment_parts)
                lines.append(f"# {comment}")

            # Формируем строку с переменной
            if is_required:
                example_value = self._get_example_value(field_type)
                lines.append(f"{env_name}={example_value}")
            else:
                formatted_value = self._format_default_value(default_value, field_type)
                lines.append(f"{env_name}={formatted_value}")

            lines.append("")

        content = "\n".join(lines).rstrip() + "\n"

        if path:
            Path(path).write_text(content, encoding="utf-8")

        return content

    def generate_markdown_docs(self) -> str:
        """Генерирует Markdown документацию.

        Returns:
            Полный Markdown документ с описанием переменных окружения
        """
        metadata = self._get_field_metadata()
        schema_name = self.schema_class.__name__

        lines = [
            "# Environment Variables Configuration",
            "",
            (
                "This document describes environment variables for "
                f"`{schema_name}` schema."
            ),
            "",
        ]

        # Общая информация
        required_count = sum(1 for m in metadata if m["is_required"])
        optional_count = len(metadata) - required_count

        lines.extend(
            [
                "## Overview",
                "",
                f"- **Total variables**: {len(metadata)}",
                f"- **Required**: {required_count}",
                f"- **Optional**: {optional_count}",
            ]
        )

        if self.prefix:
            lines.append(f"- **Prefix**: `{self.prefix}`")

        lines.extend(["", "## Variables", ""])

        # Таблица переменных
        lines.extend(
            [
                "| Variable | Type | Required | Default | Description |",
                "|----------|------|----------|---------|-------------|",
            ]
        )

        for field_info in metadata:
            env_name = field_info["env_name"]
            field_type = field_info["field_type"]
            is_required = field_info["is_required"]
            default_value = field_info["default_value"]
            description = field_info["description"]

            type_str = self._format_type_name(field_type)
            required_str = "**Yes**" if is_required else "No"
            default_str = (
                f"`{self._format_default_value(default_value, field_type)}`"
                if default_value is not None
                else "-"
            )

            description_escaped = (
                self._escape_markdown(description)
                if description
                else "*No description*"
            )

            lines.append(
                f"| `{env_name}` | `{type_str}` | {required_str} | "
                f"{default_str} | {description_escaped} |"
            )

        lines.extend(["", "## Usage Example", ""])
        lines.append("Create a `.env` file in your project root:")
        lines.extend(["", "```bash"])

        # Примеры для первых 5 полей
        for field_info in metadata[:5]:
            env_name = field_info["env_name"]
            is_required = field_info["is_required"]
            default_value = field_info["default_value"]
            field_type = field_info["field_type"]

            if is_required:
                example_value = self._get_example_value(field_type)
                lines.append(f"{env_name}={example_value}")
            elif default_value is not None:
                formatted_value = self._format_default_value(default_value, field_type)
                lines.append(f"{env_name}={formatted_value}")

        if len(metadata) > 5:
            lines.append("# ... (other variables)")

        lines.extend(["```", ""])

        # Примечания
        lines.extend(
            [
                "## Notes",
                "",
                "- **Required** variables must be set before running the application",
                "- Variables with defaults are optional and use them if not set",
                "- Boolean values: `true`, `false`, `yes`, `no`, `1`, `0`, `on`, `off`",
                "- List values accept comma-separated values or JSON arrays",
                "",
            ]
        )

        return "\n".join(lines)
