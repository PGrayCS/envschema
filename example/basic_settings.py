from envschema import EnvSchema, Field


class Settings(EnvSchema):
    """Простейшая схема настроек приложения."""

    host: str = "localhost"
    port: int
    debug: bool = False
    api_key: str = Field(description="API key for external service")


if __name__ == "__main__":
    settings = Settings.load()
    print(settings)
