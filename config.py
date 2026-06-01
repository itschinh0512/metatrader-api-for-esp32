# config.py
import os
from pathlib import Path


def _load_dotenv(path=".env"):
    env_path = Path(path)
    if not env_path.exists():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def _get_int(name, default):
    value = os.getenv(name)
    if value in (None, ""):
        return default
    return int(value)


def _get_float(name, default):
    value = os.getenv(name)
    if value in (None, ""):
        return default
    return float(value)


def _get_list(name, default):
    value = os.getenv(name)
    if value in (None, ""):
        return default
    return [item.strip().upper() for item in value.split(",") if item.strip()]


_load_dotenv()

MT5_LOGIN = _get_int("MT5_LOGIN", 0)
MT5_PASSWORD = os.getenv("MT5_PASSWORD", "")
MT5_SERVER = os.getenv("MT5_SERVER", "")

FLASK_HOST = os.getenv("FLASK_HOST", "0.0.0.0")
FLASK_PORT = _get_int("FLASK_PORT", 5000)
FLASK_DEBUG = os.getenv("FLASK_DEBUG", "false").lower() == "true"

API_KEY = os.getenv("API_KEY", "")
SYMBOLS = _get_list("SYMBOLS", ["EURUSD", "GBPUSD", "XAUUSD"])
MAX_CANDLES = _get_int("MAX_CANDLES", 500)
DEFAULT_DEVIATION = _get_int("DEFAULT_DEVIATION", 20)
DEFAULT_MAGIC = _get_int("DEFAULT_MAGIC", 20260601)
DEFAULT_LOT = _get_float("DEFAULT_LOT", 0.01)
