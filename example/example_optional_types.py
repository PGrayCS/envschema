"""Примеры использования Optional типов."""

from envschema import EnvSchema, Field


def example_basic_optional() -> None:
    """Базовый пример использования Optional."""
    print("=== Пример 1: Базовое использование Optional ===\n")

    class Settings(EnvSchema):
        # Обязательное поле
        database_url: str

        # Optional поля (могут отсутствовать)
        api_key: str | None
        cache_url: str | None
        redis_url: str | None

    # Только обязательное поле
    env = {"DATABASE_URL": "postgres://localhost/mydb"}

    settings = Settings.load(env=env)

    print(f"Database URL: {settings.database_url}")
    print(f"API Key: {settings.api_key}")  # None
    print(f"Cache URL: {settings.cache_url}")  # None
    print(f"Redis URL: {settings.redis_url}")  # None


def example_optional_with_values() -> None:
    """Пример Optional полей с предоставленными значениями."""
    print("\n=== Пример 2: Optional с значениями ===\n")

    class Settings(EnvSchema):
        database_url: str
        api_key: str | None
        cache_ttl: int | None
        debug: bool | None

    env = {
        "DATABASE_URL": "postgres://localhost/mydb",
        "API_KEY": "secret_api_key_123",
        "CACHE_TTL": "3600",
        "DEBUG": "true",
    }

    settings = Settings.load(env=env)

    print(f"Database URL: {settings.database_url}")
    print(f"API Key: {settings.api_key}")  # secret_api_key_123
    print(f"Cache TTL: {settings.cache_ttl}")  # 3600
    print(f"Debug: {settings.debug}")  # True


def example_optional_vs_default() -> None:
    """Пример разницы между Optional и дефолтными значениями."""
    print("\n=== Пример 3: Optional vs Default ===\n")

    class Settings(EnvSchema):
        # Optional: None если не указано
        api_key: str | None

        # Default: всегда имеет значение
        timeout: int = 30

        # Optional с дефолтом: может быть перезаписано
        retry_count: int | None = 3

    env = {}  # Пустое окружение

    settings = Settings.load(env=env)

    print(f"API Key (Optional): {settings.api_key}")  # None
    print(f"Timeout (Default): {settings.timeout}")  # 30
    print(f"Retry Count (Optional + Default): {settings.retry_count}")  # 3

    print("\nСемантика:")
    print("- Optional[str]: 'может отсутствовать'")
    print("- str с дефолтом: 'всегда имеет значение'")
    print("- Optional[int] = 3: 'может быть перезаписано, иначе 3'")


def example_real_world_config() -> None:
    """Реальный пример конфигурации приложения."""
    print("\n=== Пример 4: Реальная конфигурация ===\n")

    class Settings(EnvSchema):
        # Обязательные настройки
        app_name: str
        database_url: str
        secret_key: str

        # Опциональные интеграции
        sentry_dsn: str | None = Field(description="Sentry DSN for error tracking")
        slack_webhook: str | None = Field(description="Slack webhook for notifications")
        datadog_api_key: str | None = Field(description="Datadog API key for metrics")

        # Опциональные настройки с дефолтами
        log_level: str = "INFO"
        workers: int = 4
        debug: bool = False

        # Опциональные фичи
        enable_cache: bool | None = Field(description="Enable Redis caching")
        cache_ttl: int | None = Field(description="Cache TTL in seconds")

    env = {
        "APP_NAME": "MyApp",
        "DATABASE_URL": "postgres://localhost/myapp",
        "SECRET_KEY": "super-secret-key",
        "SENTRY_DSN": "https://sentry.io/project/123",
        "LOG_LEVEL": "DEBUG",
        "ENABLE_CACHE": "true",
    }

    settings = Settings.load(env=env)

    print(f"App Name: {settings.app_name}")
    print(f"Database: {settings.database_url}")
    print(f"Log Level: {settings.log_level}")
    print("\nИнтеграции:")
    print(f"  Sentry: {settings.sentry_dsn}")
    print(f"  Slack: {settings.slack_webhook or 'Not configured'}")
    print(f"  Datadog: {settings.datadog_api_key or 'Not configured'}")
    print("\nКеширование:")
    print(f"  Enabled: {settings.enable_cache}")
    print(f"  TTL: {settings.cache_ttl or 'Default'}")


def example_optional_third_party_services() -> None:
    """Пример настройки опциональных сторонних сервисов."""
    print("\n=== Пример 5: Опциональные сервисы ===\n")

    class EmailSettings(EnvSchema):
        smtp_host: str
        smtp_port: int = 587
        username: str
        password: str
        from_email: str

    class S3Settings(EnvSchema):
        bucket: str
        region: str = "us-east-1"
        access_key: str
        secret_key: str

    class Settings(EnvSchema):
        app_name: str

        # Email опционален (можно использовать mock в разработке)
        email_enabled: bool | None
        email: EmailSettings | None = Field(prefix="EMAIL_")

        # S3 опционален (можно использовать локальное хранилище)
        s3_enabled: bool | None
        s3: S3Settings | None = Field(prefix="S3_")

    # Production: все сервисы включены
    prod_env = {
        "APP_NAME": "MyApp",
        "EMAIL_ENABLED": "true",
        "EMAIL_SMTP_HOST": "smtp.gmail.com",
        "EMAIL_USERNAME": "app@example.com",
        "EMAIL_PASSWORD": "password",
        "EMAIL_FROM_EMAIL": "noreply@example.com",
        "S3_ENABLED": "true",
        "S3_BUCKET": "my-bucket",
        "S3_ACCESS_KEY": "key",
        "S3_SECRET_KEY": "secret",
    }

    # Development: все опционально
    dev_env = {"APP_NAME": "MyApp-Dev"}

    print("Production настройки:")
    prod_settings = Settings.load(env=prod_env)
    print(f"  Email enabled: {prod_settings.email_enabled}")
    print(f"  S3 enabled: {prod_settings.s3_enabled}")

    print("\nDevelopment настройки:")
    dev_settings = Settings.load(env=dev_env)
    print(f"  Email enabled: {dev_settings.email_enabled}")
    print(f"  S3 enabled: {dev_settings.s3_enabled}")
    print("  (используются моки/локальные сервисы)")


def example_optional_type_hints() -> None:
    """Пример использования разных синтаксисов Optional."""
    print("\n=== Пример 6: Синтаксис Optional ===\n")

    class Settings(EnvSchema):
        # Все эти объявления эквивалентны
        field1: str | None  # Стандартный Optional
        field2: str | None  # Union синтаксис
        field3: str | None  # Python 3.10+ синтаксис

    env = {}

    settings = Settings.load(env=env)

    print(f"field1 (Optional[str]): {settings.field1}")
    print(f"field2 (Union[str, None]): {settings.field2}")
    print(f"field3 (str | None): {settings.field3}")
    print("\nВсе три поля возвращают None")


def example_optional_validation() -> None:
    """Пример валидации Optional полей."""
    print("\n=== Пример 7: Валидация Optional ===\n")

    from envschema import EnvSchemaError

    class Settings(EnvSchema):
        port: int | None
        timeout: float | None
        debug: bool | None

    # Валидные значения
    valid_env = {
        "PORT": "8080",
        "TIMEOUT": "30.5",
        "DEBUG": "true",
    }

    settings = Settings.load(env=valid_env)
    print("Валидные значения:")
    print(f"  Port: {settings.port}")
    print(f"  Timeout: {settings.timeout}")
    print(f"  Debug: {settings.debug}")

    # Невалидные значения
    invalid_env = {
        "PORT": "not_a_number",
        "TIMEOUT": "not_a_float",
    }

    print("\nНевалидные значения:")
    try:
        Settings.load(env=invalid_env)
    except EnvSchemaError as e:
        print(f"  Найдено ошибок: {len(e.errors)}")
        for error in e.errors:
            print(f"    • {error.env_var}: {error.message}")


def example_migration_guide() -> None:
    """Пример миграции на Optional типы."""
    print("\n=== Пример 8: Миграция на Optional ===\n")

    # Старый стиль (до Optional)
    class OldSettings(EnvSchema):
        api_key: str = Field(default=None)  # type: ignore
        timeout: int = Field(default=None)  # type: ignore

    # Новый стиль (с Optional)
    class NewSettings(EnvSchema):
        api_key: str | None  # Чисто и семантично
        timeout: int | None  # Тип проверяется статически

    print("Старый стиль:")
    print("  api_key: str = Field(default=None)")
    print("  ❌ Противоречит типу (str не может быть None)")
    print("  ❌ Требует type: ignore")

    print("\nНовый стиль:")
    print("  api_key: Optional[str]")
    print("  ✅ Семантически корректно")
    print("  ✅ IDE и mypy понимают тип")
    print("  ✅ Явно показывает намерение")


if __name__ == "__main__":
    example_basic_optional()
    example_optional_with_values()
    example_optional_vs_default()
    example_real_world_config()
    example_optional_third_party_services()
    example_optional_type_hints()
    example_optional_validation()
    example_migration_guide()
