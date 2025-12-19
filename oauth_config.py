import os
import sys
import base64
from typing import Optional, Callable

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DEFAULT_CLIENT_SECRET_FILE = os.path.join(BASE_DIR, "client_secret.json")
EMBEDDED_SECRET_DIR = os.path.join(BASE_DIR, "data", "auth")
EMBEDDED_SECRET_FILENAME = "client_secret.embedded.json"

EMBEDDED_CLIENT_SECRET_B64 = os.environ.get("EMBEDDED_CLIENT_SECRET_B64", "").strip()

if not EMBEDDED_CLIENT_SECRET_B64:
    EMBEDDED_CLIENT_SECRET_B64 = ""

_cached_client_secret_path: Optional[str] = None


def _status(callback: Optional[Callable], message: str):
    if callback:
        callback("status", message)
    else:
        print(message)


def has_embedded_secret() -> bool:
    return bool(EMBEDDED_CLIENT_SECRET_B64)


def has_client_secret_source() -> bool:
    return os.path.exists(DEFAULT_CLIENT_SECRET_FILE) or has_embedded_secret()


def _write_embedded_secret() -> str:
    """Automatically creates client_secret.json from embedded base64 on first run"""
    data = base64.b64decode(EMBEDDED_CLIENT_SECRET_B64)
    with open(DEFAULT_CLIENT_SECRET_FILE, "wb") as f:
        f.write(data)
    return DEFAULT_CLIENT_SECRET_FILE


def get_client_secret_path(status_callback: Optional[Callable] = None) -> str:
    global _cached_client_secret_path
    if _cached_client_secret_path and os.path.exists(_cached_client_secret_path):
        return _cached_client_secret_path

    if os.path.exists(DEFAULT_CLIENT_SECRET_FILE):
        _cached_client_secret_path = DEFAULT_CLIENT_SECRET_FILE
        return _cached_client_secret_path

    if has_embedded_secret():
        try:
            path = _write_embedded_secret()
            _cached_client_secret_path = path
            return path
        except Exception:
            pass

    return DEFAULT_CLIENT_SECRET_FILE

