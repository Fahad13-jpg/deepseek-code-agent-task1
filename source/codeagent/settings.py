"""Per-user preferences and optional Windows DPAPI protection for API keys."""
from __future__ import annotations

import base64
import ctypes
import json
import os
from pathlib import Path
from ctypes import wintypes

from .workspace import atomic_text


def settings_path() -> Path:
    return Path(os.environ.get("LOCALAPPDATA", str(Path.home() / ".config"))) / "DeepSeekCodeAgent" / "settings.json"


def protect(data: bytes, decrypt=False) -> bytes:
    if os.name != "nt":
        raise OSError("Remembering keys is supported only with Windows DPAPI.")
    class Blob(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_ubyte))]
    buffer = ctypes.create_string_buffer(data)
    source = Blob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte)))
    target = Blob()
    crypt = ctypes.WinDLL("crypt32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    fn = crypt.CryptUnprotectData if decrypt else crypt.CryptProtectData
    fn.argtypes = [ctypes.POINTER(Blob), ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
                   ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(Blob)]
    fn.restype = wintypes.BOOL
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    kernel.LocalFree.restype = ctypes.c_void_p
    if not fn(ctypes.byref(source), None, None, None, None, 1, ctypes.byref(target)):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        return ctypes.string_at(target.pbData, target.cbData)
    finally:
        kernel.LocalFree(target.pbData)


def load_settings() -> dict:
    try:
        value = json.loads(settings_path().read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            return {}
        if value.get("protected_key"):
            try:
                value["api_key"] = protect(base64.b64decode(value["protected_key"]), decrypt=True).decode()
            except (OSError, ValueError, UnicodeError):
                value.pop("protected_key", None)
        return value
    except (OSError, ValueError):
        return {}


def save_settings(values: dict, api_key: str = "", remember: bool = False):
    safe = {k: v for k, v in values.items() if k not in {"api_key", "protected_key"}}
    if remember and api_key:
        safe["protected_key"] = base64.b64encode(protect(api_key.encode())).decode("ascii")
    atomic_text(settings_path(), json.dumps(safe, indent=2))
