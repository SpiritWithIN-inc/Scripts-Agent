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
from typing import Any, Callable

from scripts.common.logger import get_logger

log = get_logger(__name__)
_LOAD_DOTENV: Callable[..., bool] | None | bool = None


def _get_load_dotenv() -> Callable[..., bool] | None:
    """Return cached dotenv loader or None when python-dotenv is unavailable."""
    global _LOAD_DOTENV
    if _LOAD_DOTENV is False:
        return None
    if _LOAD_DOTENV is None:
        try:
            from dotenv import load_dotenv  # type: ignore[import-untyped]

            _LOAD_DOTENV = load_dotenv
        except ImportError:
            _LOAD_DOTENV = False
            log.debug("python-dotenv not installed; skipping .env loading.")
            return None
    return _LOAD_DOTENV


def load_config(dotenv_path: str | None = None) -> dict[str, Any]:
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
    load_dotenv = _get_load_dotenv()
    if load_dotenv is not None:
        if dotenv_path:
            loaded = load_dotenv(dotenv_path, override=False)
            if loaded:
                log.debug("Loaded .env from '%s'.", dotenv_path)
        else:
            loaded = load_dotenv(override=False)
            if loaded:
                log.debug("Loaded .env from current directory.")

    return dict(os.environ)


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
