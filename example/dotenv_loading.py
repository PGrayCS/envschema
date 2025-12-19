from envschema import EnvSchema


class Settings(EnvSchema):
    """Загрузка переменных из .env файла."""

    debug: bool = False
    port: int


if __name__ == "__main__":
    # Явный путь
    settings = Settings.load(dotenv_path=".env")
    print(settings)

    # Автопоиск .env вверх по директориям
    settings = Settings.load(dotenv_path=True)
    print(settings)
