from envschema import EnvSchema, Field


class DatabaseSettings(EnvSchema):
    """Настройки базы данных."""

    host: str
    port: int = 5432
    user: str
    password: str


class Settings(EnvSchema):
    """Основная схема приложения."""

    debug: bool = False
    db: DatabaseSettings = Field(prefix="DB_")


if __name__ == "__main__":
    settings = Settings.load()
    print(settings)
    print(settings.db.host)
