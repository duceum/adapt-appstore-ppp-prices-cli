from __future__ import annotations

import os
from pathlib import Path

APP_NAME = "ppp-pricing"
CONFIG_ENV_VAR = "PPP_PRICING_CONFIG"


def user_config_dir() -> Path:
    """~/.config/ppp-pricing (honours XDG_CONFIG_HOME)."""
    base = os.getenv("XDG_CONFIG_HOME") or Path.home() / ".config"
    return Path(base).expanduser().resolve() / APP_NAME


def user_cache_dir() -> Path:
    """~/.cache/ppp-pricing (honours XDG_CACHE_HOME)."""
    base = os.getenv("XDG_CACHE_HOME") or Path.home() / ".cache"
    return Path(base).expanduser().resolve() / APP_NAME


def resolve_config_dir(explicit: str | None = None) -> Path:
    """Directory holding .env and the .p8 key.

    An explicit --config or $PPP_PRICING_CONFIG wins even when it holds no
    .env, so a wrong path fails loudly instead of silently falling back.
    Otherwise: the nearest ancestor of the current directory holding a .env
    (the git-clone workflow, from any subdirectory), else the user config dir.
    """
    if explicit:
        return Path(explicit).expanduser().resolve()
    if env_dir := os.getenv(CONFIG_ENV_VAR):
        return Path(env_dir).expanduser().resolve()
    cwd = Path.cwd().resolve()
    for directory in (cwd, *cwd.parents):
        if (directory / ".env").exists():
            return directory
    return user_config_dir()
