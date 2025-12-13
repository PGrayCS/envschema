import os
from pathlib import Path


def load_dotenv(dotenv_path: str | Path | bool) -> dict[str, str]:
    """Загружает переменные из .env файла.

    Использует python-dotenv если доступен, иначе выдает понятную ошибку.

    Args:
        dotenv_path: Путь к .env файлу, True для автопоиска, или False

    Returns:
        Словарь переменных окружения из файла

    Raises:
        ImportError: Если python-dotenv не установлен
        FileNotFoundError: Если указанный файл не существует
    """
    try:
        from dotenv import dotenv_values  # type: ignore[import-not-found]
    except ImportError as e:
        raise ImportError(
            "python-dotenv is required for .env file support. "
            "Install it with: pip install envschema[dotenv] "
            "or pip install python-dotenv"
        ) from e

    if isinstance(dotenv_path, bool):
        if dotenv_path:
            file_path = Path.cwd() / ".env"
        else:
            return {}
    else:
        file_path = Path(dotenv_path)

    if not file_path.exists():
        raise FileNotFoundError(f".env file not found: {file_path}")

    env_vars = dotenv_values(str(file_path))

    return {k: v for k, v in env_vars.items() if v is not None}


def merge_env_sources(
    dotenv_vars: dict[str, str],
    system_env: dict[str, str] | None = None,
) -> dict[str, str]:
    """Объединяет переменные из .env и системного окружения.

    Приоритет: system_env > dotenv_vars
    (системные переменные перезаписывают значения из .env)

    Args:
        dotenv_vars: Переменные из .env файла
        system_env: Системные переменные окружения (по умолчанию os.environ)

    Returns:
        Объединенный словарь переменных
    """
    if system_env is None:
        system_env = dict(os.environ)

    merged = {}
    merged.update(dotenv_vars)
    merged.update(system_env)

    return merged


def load_env_with_dotenv(
    dotenv_path: str | Path | bool | None = None,
    override: bool = False,
) -> dict[str, str]:
    """Загружает переменные окружения с поддержкой .env файлов.

    Args:
        dotenv_path: Путь к .env файлу, True для автопоиска, None для игнора
        override: Если True, .env перезаписывает системные переменные

    Returns:
        Словарь переменных окружения

    Example:
        >>> env = load_env_with_dotenv(".env")
        >>> env = load_env_with_dotenv(True)  # Автопоиск .env
        >>> env = load_env_with_dotenv()  # Только os.environ
    """
    if dotenv_path is None:
        return dict(os.environ)

    dotenv_vars = load_dotenv(dotenv_path)

    if override:
        merged = dict(os.environ)
        merged.update(dotenv_vars)
        return merged
    else:
        return merge_env_sources(dotenv_vars)
