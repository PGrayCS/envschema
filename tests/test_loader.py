"""Тесты для модуля loader.py."""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from envschema.loader import (
    load_dotenv,
    load_env_with_dotenv,
    merge_env_sources,
)


@pytest.fixture(autouse=True)
def mock_dotenv() -> None:
    """Мокает модуль dotenv для всех тестов."""
    mock_dotenv_module = MagicMock()
    mock_dotenv_module.dotenv_values = MagicMock()

    with patch.dict("sys.modules", {"dotenv": mock_dotenv_module}):
        yield


class TestLoadDotenv:
    """Тесты для функции load_dotenv."""

    def test_load_dotenv_with_string_path(self) -> None:
        """Проверяет загрузку .env файла по строковому пути."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("KEY1=value1\nKEY2=value2\nKEY3=value3\n")
            temp_path = f.name

        try:
            sys.modules["dotenv"].dotenv_values.return_value = {
                "KEY1": "value1",
                "KEY2": "value2",
                "KEY3": "value3",
            }

            result = load_dotenv(temp_path)
            assert result == {
                "KEY1": "value1",
                "KEY2": "value2",
                "KEY3": "value3",
            }
            sys.modules["dotenv"].dotenv_values.assert_called_once_with(temp_path)
        finally:
            os.unlink(temp_path)

    def test_load_dotenv_with_path_object(self) -> None:
        """Проверяет загрузку .env файла по объекту Path."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("TEST_KEY=test_value\n")
            temp_path = Path(f.name)

        try:
            sys.modules["dotenv"].dotenv_values.return_value = {
                "TEST_KEY": "test_value"
            }

            result = load_dotenv(temp_path)
            assert result == {"TEST_KEY": "test_value"}
            sys.modules["dotenv"].dotenv_values.assert_called_once_with(str(temp_path))
        finally:
            os.unlink(str(temp_path))

    def test_load_dotenv_with_bool_true(self, tmp_path: Path) -> None:
        """Проверяет автопоиск .env файла при dotenv_path=True."""
        env_file = tmp_path / ".env"
        env_file.write_text("AUTO_KEY=auto_value\n")

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            sys.modules["dotenv"].dotenv_values.return_value = {
                "AUTO_KEY": "auto_value"
            }

            result = load_dotenv(True)
            assert result == {"AUTO_KEY": "auto_value"}
        finally:
            os.chdir(original_cwd)

    def test_load_dotenv_with_bool_false(self) -> None:
        """Проверяет возврат пустого словаря при dotenv_path=False."""
        result = load_dotenv(False)
        assert result == {}

    def test_load_dotenv_filters_none_values(self) -> None:
        """Проверяет фильтрацию None значений из .env файла."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("KEY1=value1\nKEY2=\nKEY3=value3\n")
            temp_path = f.name

        try:
            sys.modules["dotenv"].dotenv_values.return_value = {
                "KEY1": "value1",
                "KEY2": None,
                "KEY3": "value3",
            }

            result = load_dotenv(temp_path)
            assert "KEY1" in result
            assert "KEY2" not in result
            assert "KEY3" in result
            assert result["KEY1"] == "value1"
            assert result["KEY3"] == "value3"
        finally:
            os.unlink(temp_path)

    def test_load_dotenv_file_not_found(self) -> None:
        """Проверяет ошибку при отсутствии .env файла."""
        non_existent = Path("/non/existent/path/.env")

        with pytest.raises(FileNotFoundError) as exc_info:
            load_dotenv(non_existent)

        assert ".env file not found" in str(exc_info.value)
        assert str(non_existent) in str(exc_info.value)

    def test_load_dotenv_import_error(self) -> None:
        """Проверяет ошибку при отсутствии python-dotenv."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            temp_path = f.name

        try:
            # Временно удаляем мок dotenv для этого теста
            with patch.dict("sys.modules", {"dotenv": None}):
                with pytest.raises(ImportError) as exc_info:
                    load_dotenv(temp_path)

                error_msg = str(exc_info.value)
                assert "python-dotenv is required" in error_msg
                assert "pip install" in error_msg
        finally:
            os.unlink(temp_path)


class TestMergeEnvSources:
    """Тесты для функции merge_env_sources."""

    def test_merge_basic(self) -> None:
        """Проверяет базовое объединение переменных."""
        dotenv_vars = {"KEY1": "dotenv_value1", "KEY2": "dotenv_value2"}
        system_env = {"KEY2": "system_value2", "KEY3": "system_value3"}

        result = merge_env_sources(dotenv_vars, system_env)

        assert result["KEY1"] == "dotenv_value1"
        assert result["KEY2"] == "system_value2"
        assert result["KEY3"] == "system_value3"

    def test_merge_system_env_priority(self) -> None:
        """Проверяет приоритет system_env над dotenv_vars."""
        dotenv_vars = {"CONFLICT_KEY": "dotenv_value"}
        system_env = {"CONFLICT_KEY": "system_value"}

        result = merge_env_sources(dotenv_vars, system_env)

        assert result["CONFLICT_KEY"] == "system_value"

    def test_merge_with_none_system_env(self) -> None:
        """Проверяет использование os.environ при system_env=None."""
        dotenv_vars = {"DOTENV_KEY": "dotenv_value"}

        original_env = dict(os.environ)

        try:
            os.environ.clear()
            os.environ["SYSTEM_KEY"] = "system_value"
            os.environ["DOTENV_KEY"] = "system_override"

            result = merge_env_sources(dotenv_vars, None)

            assert result["DOTENV_KEY"] == "system_override"
            assert result["SYSTEM_KEY"] == "system_value"
        finally:
            os.environ.clear()
            os.environ.update(original_env)

    def test_merge_empty_dotenv(self) -> None:
        """Проверяет объединение с пустым dotenv_vars."""
        system_env = {"KEY1": "value1", "KEY2": "value2"}

        result = merge_env_sources({}, system_env)

        assert result == system_env

    def test_merge_empty_system_env(self) -> None:
        """Проверяет объединение с пустым system_env."""
        dotenv_vars = {"KEY1": "value1", "KEY2": "value2"}

        result = merge_env_sources(dotenv_vars, {})

        assert result == dotenv_vars

    def test_merge_both_empty(self) -> None:
        """Проверяет объединение двух пустых словарей."""
        result = merge_env_sources({}, {})

        assert result == {}


class TestLoadEnvWithDotenv:
    """Тесты для функции load_env_with_dotenv."""

    def test_load_with_none_dotenv_path(self) -> None:
        """Проверяет загрузку только os.environ при dotenv_path=None."""
        original_env = dict(os.environ)

        try:
            os.environ.clear()
            os.environ["TEST_KEY"] = "test_value"

            result = load_env_with_dotenv(dotenv_path=None)

            assert "TEST_KEY" in result
            assert result["TEST_KEY"] == "test_value"
        finally:
            os.environ.clear()
            os.environ.update(original_env)

    def test_load_with_string_path(self) -> None:
        """Проверяет загрузку с указанием строкового пути."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("DOTENV_KEY=dotenv_value\n")
            temp_path = f.name

        original_env = dict(os.environ)

        try:
            os.environ.clear()
            os.environ["SYSTEM_KEY"] = "system_value"
            os.environ["DOTENV_KEY"] = "system_override"

            sys.modules["dotenv"].dotenv_values.return_value = {
                "DOTENV_KEY": "dotenv_value"
            }

            result = load_env_with_dotenv(dotenv_path=temp_path, override=False)

            assert result["DOTENV_KEY"] == "system_override"
            assert result["SYSTEM_KEY"] == "system_value"
        finally:
            os.unlink(temp_path)
            os.environ.clear()
            os.environ.update(original_env)

    def test_load_with_path_object(self) -> None:
        """Проверяет загрузку с указанием объекта Path."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("PATH_KEY=path_value\n")
            temp_path = Path(f.name)

        original_env = dict(os.environ)

        try:
            os.environ.clear()
            sys.modules["dotenv"].dotenv_values.return_value = {
                "PATH_KEY": "path_value"
            }

            result = load_env_with_dotenv(dotenv_path=temp_path)

            assert result["PATH_KEY"] == "path_value"
        finally:
            os.unlink(str(temp_path))
            os.environ.clear()
            os.environ.update(original_env)

    def test_load_with_bool_true(self, tmp_path: Path) -> None:
        """Проверяет автопоиск .env файла при dotenv_path=True."""
        env_file = tmp_path / ".env"
        env_file.write_text("AUTO_KEY=auto_value\n")

        original_cwd = os.getcwd()
        original_env = dict(os.environ)

        try:
            os.environ.clear()
            os.chdir(tmp_path)
            sys.modules["dotenv"].dotenv_values.return_value = {
                "AUTO_KEY": "auto_value"
            }

            result = load_env_with_dotenv(dotenv_path=True)

            assert result["AUTO_KEY"] == "auto_value"
        finally:
            os.chdir(original_cwd)
            os.environ.clear()
            os.environ.update(original_env)

    def test_load_with_override_false(self) -> None:
        """Проверяет режим override=False (system_env имеет приоритет)."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("CONFLICT_KEY=dotenv_value\n")
            temp_path = f.name

        original_env = dict(os.environ)

        try:
            os.environ.clear()
            os.environ["CONFLICT_KEY"] = "system_value"

            sys.modules["dotenv"].dotenv_values.return_value = {
                "CONFLICT_KEY": "dotenv_value"
            }

            result = load_env_with_dotenv(dotenv_path=temp_path, override=False)

            assert result["CONFLICT_KEY"] == "system_value"
        finally:
            os.unlink(temp_path)
            os.environ.clear()
            os.environ.update(original_env)

    def test_load_with_override_true(self) -> None:
        """Проверяет режим override=True (dotenv перезаписывает system)."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("CONFLICT_KEY=dotenv_value\n")
            temp_path = f.name

        original_env = dict(os.environ)

        try:
            os.environ.clear()
            os.environ["CONFLICT_KEY"] = "system_value"
            os.environ["SYSTEM_ONLY_KEY"] = "system_only"

            sys.modules["dotenv"].dotenv_values.return_value = {
                "CONFLICT_KEY": "dotenv_value"
            }

            result = load_env_with_dotenv(dotenv_path=temp_path, override=True)

            assert result["CONFLICT_KEY"] == "dotenv_value"
            assert result["SYSTEM_ONLY_KEY"] == "system_only"
        finally:
            os.unlink(temp_path)
            os.environ.clear()
            os.environ.update(original_env)

    def test_load_file_not_found(self) -> None:
        """Проверяет ошибку при отсутствии .env файла."""
        non_existent = Path("/non/existent/path/.env")

        with pytest.raises(FileNotFoundError):
            load_env_with_dotenv(dotenv_path=non_existent)
