import hashlib
import hmac
import secrets
import time
from collections import defaultdict

from .config import LOGIN_MAX_FAILS, LOGIN_WINDOW_SECONDS

_ITERATIONS = 200_000


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), _ITERATIONS)
    return f"pbkdf2${_ITERATIONS}${salt}${digest.hex()}"


# Used so a missing account costs the same time as a wrong password.
_DUMMY = hash_password("dummy-password")


def verify_password(password: str, stored: str | None) -> bool:
    ok_format = bool(stored)
    try:
        _, iters, salt, digest = (stored or _DUMMY).split("$")
        calc = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), int(iters))
        match = hmac.compare_digest(calc.hex(), digest)
    except Exception:
        return False
    return match and ok_format


# --- tiny in-memory login throttle (per process; fine for a single Render instance) ---
_fails: dict[tuple[str, str], list[float]] = defaultdict(list)


def _recent(key: tuple[str, str]) -> list[float]:
    cutoff = time.time() - LOGIN_WINDOW_SECONDS
    _fails[key] = [t for t in _fails[key] if t > cutoff]
    return _fails[key]


def login_blocked(ip: str, chatid: str) -> bool:
    return len(_recent((ip, chatid))) >= LOGIN_MAX_FAILS


def login_failed(ip: str, chatid: str) -> None:
    _recent((ip, chatid)).append(time.time())


def login_ok(ip: str, chatid: str) -> None:
    _fails.pop((ip, chatid), None)
