
"""Модуль для генерации документации из схем EnvSchema."""

import json
from pathlib import Path
from typing import Any, get_args, get_origin

from .schema import EnvSchema
from .field import Field


class DocumentationGenerator:
    """Генератор документации для EnvSchema.
    
    Attributes:
    schema_class: Класс схемы EnvSchema
    prefix: Префикс для переменных окружения
    """

    def __init__(
        self,
        schema_class,
        prefix: str | None = None,
    ) -> None:
        """Инициализирует генератор.

        Args:
            schema_class: Класс схемы EnvSchema
            prefix: Префикс для переменных окружения (по умолчанию "")
        """
        self.schema_class = schema_class
        self.prefix = prefix
        self._metadata_cache: list[dict[str, Any]] | None = None

    def _collect_metadata(self) -> list[dict[str, Any]]:
        """Собирает метаданные полей схемы.
        
        Returns:
            Список словарей с метаданными каждого поля
        """
        fields = self.schema_class._get_fields()
        metadata = []
        prefix = self.prefix or ""
        
        for field_name, (field, field_type) in fields.items():
            env_name = field.get_env_name(prefix)
            is_required = not field.has_default()
            
            if field.has_default():
                default_value = field.get_default()
            else:
                default_value = None
            
            description = field.description or ""
            
            metadata.append({
                "field_name": field_name,
                "env_name": env_name,
                "field_type": field_type,
                "is_required": is_required,
                "default_value": default_value,
                "description": description,
            })
        
        return metadata
    
    def _get_field_metadata(self) -> list[dict[str, Any]]:
        """Получает метаданные полей (с кешированием).
        
        Returns:
            Список словарей с метаданными каждого поля
        """
        if self._metadata_cache is None:
            self._metadata_cache = self._collect_metadata()
        return self._metadata_cache
    
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
        
        if field_type is bool:
            return str(value).lower()
        
        if field_type is str:
            return str(value)
        
        if field_type in (int, float):
            return str(value)
        
        # Обработка list[T]
        origin = get_origin(field_type)
        if origin is list:
            args = get_args(field_type)
            item_type = args[0] if args else str
            
            if item_type is str:
                # Для list[str] используем CSV формат
                return ",".join(str(item) for item in value)
            else:
                # Для других типов - JSON массив
                return json.dumps(value)
        
        # Обработка dict
        if field_type is dict:
            return json.dumps(value)
        
        return str(value)
    
    def _format_type_name(self, field_type: type) -> str:
        """Форматирует имя типа для документации.
        
        Args:
            field_type: Тип поля
            
        Returns:
            Строковое представление типа
        """
        origin = get_origin(field_type)
        
        if origin is list:
            args = get_args(field_type)
            item_type = args[0] if args else str
            return f"list[{item_type.__name__}]"
        
        return field_type.__name__
    
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
        text = text.replace("\\", "\\\\")  # Сначала экранируем обратный слэш
        text = text.replace("|", "\\|")  # Таблицы
        text = text.replace("_", "\\_")  # Курсив/жирный
        text = text.replace("*", "\\*")  # Курсив/жирный
        text = text.replace("[", "\\[")  # Ссылки
        text = text.replace("]", "\\]")  # Ссылки
        text = text.replace("`", "\\`")  # Код
        
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
            
            # Добавляем комментарий, если есть что писать
            if comment_parts:
                comment = " ".join(comment_parts)
                lines.append(f"# {comment}")
            
            # Формируем строку с переменной
            if is_required:
                # Для обязательных полей используем placeholder
                example_value = self._get_example_value(field_type)
                lines.append(f"{env_name}={example_value}")
            else:
                # Для необязательных - значение по умолчанию
                formatted_value = self._format_default_value(
                    default_value, field_type
                )
                lines.append(f"{env_name}={formatted_value}")
            
            # Пустая строка между полями для читаемости
            lines.append("")
        
        content = "\n".join(lines).rstrip() + "\n"
        
        # Записываем в файл, если указан путь
        if path:
            Path(path).write_text(content, encoding="utf-8")
        
        return content

    def _get_example_value(self, field_type: type) -> str:
        """Получает пример значения для обязательного поля.
        
        Args:
            field_type: Тип поля
            
        Returns:
            Пример значения
        """
        origin = get_origin(field_type)
        
        if origin is list:
            args = get_args(field_type)
            item_type = args[0] if args else str
            if item_type is str:
                return "value1,value2"
            return "[1, 2, 3]"
        
        if field_type is str:
            return "your_value_here"
        
        if field_type is int:
            return "0"
        
        if field_type is float:
            return "0.0"
        
        if field_type is bool:
            return "true"
        
        if field_type is dict:
            return '{"key": "value"}'
        
        return "your_value_here"
    
    def generate_markdown_docs(self) -> str:
        """Генерирует Markdown документацию.
        
        Returns:
            Полный Markdown документ с описанием переменных окружения
        """
        metadata = self._get_field_metadata()
        schema_name = self.schema_class.__name__
        
        lines = []
        
        # Главный заголовок
        lines.append(f"# Environment Variables Configuration")
        lines.append("")
        lines.append(f"This document describes all environment variables for `{schema_name}` schema.")
        lines.append("")
        
        # Общая информация
        required_count = sum(1 for m in metadata if m["is_required"])
        optional_count = len(metadata) - required_count
        
        lines.append("## Overview")
        lines.append("")
        lines.append(f"- **Total variables**: {len(metadata)}")
        lines.append(f"- **Required**: {required_count}")
        lines.append(f"- **Optional**: {optional_count}")
        if self.prefix:
            lines.append(f"- **Prefix**: `{self.prefix}`")
        lines.append("")
        
        # Таблица переменных
        lines.append("## Variables")
        lines.append("")
        lines.append("| Variable | Type | Required | Default | Description |")
        lines.append("|----------|------|----------|---------|-------------|")
        
        # Строки таблицы
        for field_info in metadata:
            env_name = field_info["env_name"]
            field_type = field_info["field_type"]
            is_required = field_info["is_required"]
            default_value = field_info["default_value"]
            description = field_info["description"]
            
            # Форматируем значения для таблицы
            type_str = self._format_type_name(field_type)
            required_str = "**Yes**" if is_required else "No"
            
            if default_value is not None:
                default_str = f"`{self._format_default_value(default_value, field_type)}`"
            else:
                default_str = "-"
            
            # Экранируем для Markdown
            env_name_escaped = self._escape_markdown(env_name)
            description_escaped = self._escape_markdown(description) if description else "*No description*"
            
            lines.append(
                f"| `{env_name_escaped}` | `{type_str}` | {required_str} | "
                f"{default_str} | {description_escaped} |"
            )
        
        lines.append("")
        
        # Пример использования
        lines.append("## Usage Example")
        lines.append("")
        lines.append("Create a `.env` file in your project root:")
        lines.append("")
        lines.append("```bash")
        
        # Показываем примеры для нескольких полей
        example_count = 0
        for field_info in metadata[:5]:  # Первые 5 полей для примера
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
            example_count += 1
        
        if len(metadata) > example_count:
            lines.append("# ... (other variables)")
        
        lines.append("```")
        lines.append("")
        
        # Примечания
        lines.append("## Notes")
        lines.append("")
        lines.append("- Variables marked as **Required** must be set before running the application")
        lines.append("- Variables with default values are optional and will use the default if not set")
        lines.append("- Boolean values can be: `true`, `false`, `yes`, `no`, `1`, `0`, `on`, `off`")
        lines.append("- List values can be provided as comma-separated values or JSON arrays")
        lines.append("")
        
        return "\n".join(lines)
