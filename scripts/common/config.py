"""
config.py — Configuration helpers for generated scripts.

Loads settings from environment variables (and optionally a .env file when
python-dotenv is installed).  Scripts should import this module and call
``load_config()`` near the top of main().

Usage
-----
    from scripts.common.config import load_config, require_env

    cfg = load_config()
    api_key = require_env("MY_API_KEY")
"""

from __future__ import annotations

import os
from typing import Any

from scripts.common.logger import get_logger

log = get_logger(__name__)
_config_cache: dict[str, Any] | None = None
_config_cache_dotenv_path: str | None = None


def load_config(
    dotenv_path: str | None = None,
    *,
    use_cache: bool = True,
) -> dict[str, Any]:
    """Load configuration from environment variables.

    If ``python-dotenv`` is installed and a ``.env`` file exists, it is
    loaded automatically.  Variables already present in the environment
    always take precedence.

    Parameters
    ----------
    dotenv_path:
        Explicit path to a ``.env`` file.  Pass ``None`` to auto-discover.

    Returns
    -------
    dict
        A snapshot of the current environment variables.
    """
    global _config_cache, _config_cache_dotenv_path
    if use_cache and _config_cache is not None and _config_cache_dotenv_path == dotenv_path:
        return dict(_config_cache)

    try:
        from dotenv import load_dotenv  # type: ignore[import-untyped]

        if dotenv_path:
            load_dotenv(dotenv_path, override=False)
            log.debug("Loaded .env from '%s'.", dotenv_path)
        else:
            loaded = load_dotenv(override=False)
            if loaded:
                log.debug("Loaded .env from current directory.")
    except ImportError:
        log.debug("python-dotenv not installed; skipping .env loading.")

    snapshot = dict(os.environ)
    if use_cache:
        _config_cache = snapshot
        _config_cache_dotenv_path = dotenv_path
    return dict(snapshot)


def require_env(name: str, default: str | None = None) -> str:
    """Return the value of environment variable *name*.

    Parameters
    ----------
    name:
        Environment variable name.
    default:
        Value to return when the variable is absent.  If ``None`` (the
        default), raises ``RuntimeError`` when the variable is missing.

    Raises
    ------
    RuntimeError
        If *name* is not set and no *default* is provided.
    """
    value = os.environ.get(name, default)
    if value is None:
        raise RuntimeError(
            f"Required environment variable '{name}' is not set. "
            "Add it to your environment or to a .env file."
        )
    return value


def get_env(name: str, default: str = "") -> str:
    """Return the value of *name* or *default* if it is absent."""
    return os.environ.get(name, default)
