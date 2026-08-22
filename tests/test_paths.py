import os
from pathlib import Path
from unittest.mock import patch

from appstore_ppp_prices.paths import (
    APP_NAME,
    CONFIG_ENV_VAR,
    resolve_config_dir,
    user_cache_dir,
    user_config_dir,
)


class TestUserDirs:
    def test_config_dir_honours_xdg(self, tmp_path):
        with patch.dict(os.environ, {"XDG_CONFIG_HOME": str(tmp_path)}):
            assert user_config_dir() == tmp_path.resolve() / APP_NAME

    def test_cache_dir_honours_xdg(self, tmp_path):
        with patch.dict(os.environ, {"XDG_CACHE_HOME": str(tmp_path)}):
            assert user_cache_dir() == tmp_path.resolve() / APP_NAME

    def test_config_dir_defaults_to_home(self):
        with patch.dict(os.environ, {}, clear=True):
            assert user_config_dir() == Path.home().resolve() / ".config" / APP_NAME

    def test_cache_dir_defaults_to_home(self):
        with patch.dict(os.environ, {}, clear=True):
            assert user_cache_dir() == Path.home().resolve() / ".cache" / APP_NAME


class TestResolveConfigDir:
    def test_explicit_flag_wins(self, tmp_path):
        with patch.dict(os.environ, {CONFIG_ENV_VAR: "/somewhere/else"}):
            assert resolve_config_dir(str(tmp_path)) == tmp_path.resolve()

    def test_explicit_flag_expands_tilde(self):
        assert resolve_config_dir("~/keys") == (Path.home() / "keys").resolve()

    def test_explicit_flag_used_even_without_env_file(self, tmp_path):
        """A wrong --config must fail loudly, not fall back to the cwd."""
        empty = tmp_path / "empty"
        empty.mkdir()
        assert resolve_config_dir(str(empty)) == empty.resolve()

    def test_env_var_used_when_no_flag(self, tmp_path):
        with patch.dict(os.environ, {CONFIG_ENV_VAR: str(tmp_path)}):
            assert resolve_config_dir(None) == tmp_path.resolve()

    def test_env_var_used_even_without_env_file(self, tmp_path, monkeypatch):
        """Same rule as --config: an explicit path is never silently replaced."""
        cwd = tmp_path / "cwd"
        cwd.mkdir()
        (cwd / ".env").write_text("ASC_KEY_ID=x")
        monkeypatch.chdir(cwd)
        empty = tmp_path / "empty"
        empty.mkdir()
        with patch.dict(os.environ, {CONFIG_ENV_VAR: str(empty)}):
            assert resolve_config_dir(None) == empty.resolve()

    def test_falls_back_to_cwd_when_it_has_env_file(self, tmp_path, monkeypatch):
        """The git-clone workflow: run from the project folder, .env sits there."""
        (tmp_path / ".env").write_text("ASC_KEY_ID=x")
        monkeypatch.chdir(tmp_path)
        with patch.dict(os.environ, {}, clear=True):
            assert resolve_config_dir(None) == tmp_path.resolve()

    def test_finds_env_file_in_a_parent_directory(self, tmp_path, monkeypatch):
        """Running from a subdirectory of the clone still finds the project .env."""
        (tmp_path / ".env").write_text("ASC_KEY_ID=x")
        nested = tmp_path / "a" / "b"
        nested.mkdir(parents=True)
        monkeypatch.chdir(nested)
        with patch.dict(os.environ, {}, clear=True):
            assert resolve_config_dir(None) == tmp_path.resolve()

    def test_falls_back_to_user_config_when_no_env_file_anywhere(self, tmp_path, monkeypatch):
        # Path.exists is stubbed so the walk up to / cannot hit a stray real .env.
        monkeypatch.chdir(tmp_path)
        with patch.dict(os.environ, {"XDG_CONFIG_HOME": str(tmp_path / "cfg")}), \
             patch("appstore_ppp_prices.paths.Path.cwd", return_value=tmp_path):
            with patch.object(Path, "exists", return_value=False):
                assert resolve_config_dir(None) == (tmp_path / "cfg").resolve() / APP_NAME
