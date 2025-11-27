import os
import base64
from typing import Optional, Callable

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CLIENT_SECRET_FILE = os.path.join(BASE_DIR, "client_secret.json")
EMBEDDED_SECRET_DIR = os.path.join(BASE_DIR, "data", "auth")
EMBEDDED_SECRET_FILENAME = "client_secret.embedded.json"

# Можно задать клиент через переменную окружения EMBEDDED_CLIENT_SECRET_B64
# или вписать строку ниже (base64 от содержимого client_secret.json).
EMBEDDED_CLIENT_SECRET_B64 = os.environ.get("EMBEDDED_CLIENT_SECRET_B64", "").strip()

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
    os.makedirs(EMBEDDED_SECRET_DIR, exist_ok=True)
    target_path = os.path.join(EMBEDDED_SECRET_DIR, EMBEDDED_SECRET_FILENAME)
    data = base64.b64decode(EMBEDDED_CLIENT_SECRET_B64)
    with open(target_path, "wb") as f:
        f.write(data)
    return target_path


def get_client_secret_path(status_callback: Optional[Callable] = None) -> str:
    global _cached_client_secret_path
    if _cached_client_secret_path and os.path.exists(_cached_client_secret_path):
        return _cached_client_secret_path

    if os.path.exists(DEFAULT_CLIENT_SECRET_FILE):
        _cached_client_secret_path = DEFAULT_CLIENT_SECRET_FILE
        return _cached_client_secret_path

    if has_embedded_secret():
        if status_callback:
            status_callback("status", "🔐 Используем встроенный OAuth ключ.")
        path = _write_embedded_secret()
        _cached_client_secret_path = path
        return path

    raise FileNotFoundError(
        "client_secret.json не найден и EMBEDDED_CLIENT_SECRET_B64 не задан. "
        "Добавь файл рядом с приложением или задай переменную окружения."
    )

