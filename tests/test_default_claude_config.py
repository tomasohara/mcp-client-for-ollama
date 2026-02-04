"""
Tests for cross-platform support of Claude Desktop configuration
"""

import importlib
import pathlib
import platform as py_platform
import sys
from typing import Any

import pytest

CONFIG_MODULE_NAME = "mcp_client_for_ollama.config"


def _normalize_path(value: Any) -> str:
    """Return a string path with normalized separators for cross-platform comparison."""
    return str(value).replace("\\", "/")


def _get_default_claude_config(mod: Any) -> Any:
    """Obtain the default Claude config path from the config module, or skip if absent."""
    # Try common constant names
    for name in (
        "DEFAULT_CLAUDE_CONFIG",
        "DEFAULT_CLAUDE_CONFIG_PATH",
        "DEFAULT_CLAUDE_CONFIG_FILE",
    ):
        if hasattr(mod, name):
            return getattr(mod, name)

    # Try common getter names
    for fname in (
        "default_claude_config_path",
        "get_default_claude_config",
        "get_default_claude_config_path",
    ):
        if hasattr(mod, fname):
            fn = getattr(mod, fname)
            if callable(fn):
                return fn()

    pytest.skip("No default Claude config path is exposed in mcp_client_for_ollama.config")
    return None


def _reload_config(
    monkeypatch: pytest.MonkeyPatch,
    platform_value: str,
    system_value: str,
    home: str,
    appdata: str | None,
):
    """Reload the config module after patching platform, APPDATA, and home."""
    # Patch platform indicators (do NOT patch os.name to avoid WindowsPath issues on POSIX)
    monkeypatch.setattr(sys, "platform", platform_value)
    monkeypatch.setattr(py_platform, "system", lambda: system_value)

    # Patch APPDATA environment
    if appdata is None:
        monkeypatch.delenv("APPDATA", raising=False)
    else:
        monkeypatch.setenv("APPDATA", appdata)

    # Patch home directory
    monkeypatch.setattr(pathlib.Path, "home", staticmethod(lambda: pathlib.Path(home)))

    # Reload module so top-level constants recompute under patched environment
    mod = pytest.importorskip(CONFIG_MODULE_NAME)
    mod = importlib.reload(mod)
    return mod


def test_default_claude_config_macos(monkeypatch: pytest.MonkeyPatch):
    """macOS default path should use ~/Library/Application Support/Claude/claude_desktop_config.json."""
    home = "/Users/alice"
    mod = _reload_config(
        monkeypatch,
        platform_value="darwin",
        system_value="Darwin",
        home=home,
        appdata=None,
    )
    cfg = _get_default_claude_config(mod)
    expected = pathlib.Path(home) / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    assert _normalize_path(cfg) == _normalize_path(expected)


def test_default_claude_config_linux(monkeypatch: pytest.MonkeyPatch):
    """Linux default path should use ~/.config/Claude/claude_desktop_config.json."""
    home = "/home/alice"
    mod = _reload_config(
        monkeypatch,
        platform_value="linux",
        system_value="Linux",
        home=home,
        appdata=None,
    )
    cfg = _get_default_claude_config(mod)
    expected = pathlib.Path(home) / ".config" / "Claude" / "claude_desktop_config.json"
    assert _normalize_path(cfg) == _normalize_path(expected)


def test_default_claude_config_windows_with_appdata(monkeypatch: pytest.MonkeyPatch):
    """Windows path should honor APPDATA if set."""
    home = r"C:/Users/Alice"
    appdata = r"C:/Users/Alice/AppData/Roaming"
    mod = _reload_config(
        monkeypatch,
        platform_value="win32",
        system_value="Windows",
        home=home,
        appdata=appdata,
    )
    cfg = _get_default_claude_config(mod)
    expected = pathlib.Path(appdata) / "Claude" / "claude_desktop_config.json"
    assert _normalize_path(cfg) == _normalize_path(expected)


def test_default_claude_config_windows_fallback_home(monkeypatch: pytest.MonkeyPatch):
    """Windows path should fall back to home/AppData/Roaming when APPDATA is unset."""
    home = r"C:/Users/Alice"
    mod = _reload_config(
        monkeypatch,
        platform_value="win32",
        system_value="Windows",
        home=home,
        appdata=None,
    )
    cfg = _get_default_claude_config(mod)
    expected = pathlib.Path(home) / "AppData" / "Roaming" / "Claude" / "claude_desktop_config.json"
    assert _normalize_path(cfg) == _normalize_path(expected)
