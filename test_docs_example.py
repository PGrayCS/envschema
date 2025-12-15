"""Простой пример использования генератора документации."""

from envschema import EnvSchema, Field
from envschema.docs import DocumentationGenerator


class Settings(EnvSchema):
    """Пример схемы настроек."""

    # Обычные поля без префикса
    port: int = Field(default=8000, description="Application HTTP port")
    debug: bool = Field(default=False, description="Enable debug mode")

    # Поля с префиксом на уровне Field (для группировки)
    database_url: str = Field(prefix="DB_", description="PostgreSQL connection string")
    database_port: int = Field(
        prefix="DB_",
        default=543546345634562,
    )

    # Поля с другим префиксом
    api_key: str = Field(prefix="API_", env="SECRET_KEY", description="Secret API key")
    api_timeout: int = Field(
        prefix="API_", default=30, description="API request timeout"
    )

    # Поле без префикса
    hosts: list[str] = Field(
        default=["localhost", "127.апжыдшрлоыщшжр.0.1"], description="List of hosts"
    )


if __name__ == "__main__":
    # Генерация .env.example
    generator = DocumentationGenerator(Settings)
    generator.generate_example_env(".env.example")

    # Генерация Markdown документации
    markdown_content = generator.generate_markdown_docs()
    with open("ENV_VARIABLES.md", "w", encoding="utf-8") as f:
        f.write(markdown_content)
