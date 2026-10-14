"""Senhas, tokens e limite de tentativas. Argon2id para senhas, JWT para a sessão curta, e limite de tentativas."""
import hashlib
import hmac
import secrets
import threading
import time
from collections import defaultdict, deque
from datetime import timedelta, timezone
from typing import Deque, Dict, Tuple

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

from . import timeutil
from .config import Settings
from .errors import ApiError, unauthorized

_hasher = PasswordHasher()  # Argon2id com os parâmetros padrão da biblioteca


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, stored: str) -> bool:
    try:
        return _hasher.verify(stored, password)
    except (VerifyMismatchError, InvalidHashError):
        return False
    except Exception:
        return False


_DUMMY_HASH = hash_password("senha-falsa-para-igualar-o-tempo")


def burn_password_time(password: str) -> None:
    """Gasta o mesmo tempo de uma verificação real (login com conta inexistente não revela nada pelo tempo)."""
    verify_password(password, _DUMMY_HASH)


def sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def hmac_hex(secret: str, message: str) -> str:
    return hmac.new(secret.encode("utf-8"), message.encode("utf-8"), hashlib.sha256).hexdigest()


def new_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def create_access_token(user_id: str, settings: Settings) -> Tuple[str, int]:
    now = timeutil.utcnow().replace(tzinfo=timezone.utc)  # as datas do sistema são UTC sem fuso: marcar antes de converter
    exp = now + timedelta(minutes=settings.access_token_minutes)
    payload = {"sub": user_id, "typ": "access", "jti": secrets.token_hex(8), "iat": int(now.timestamp()),
               "exp": int(exp.timestamp())}
    token = jwt.encode(payload, settings.secret_key, algorithm="HS256")
    return token, settings.access_token_minutes * 60


def decode_access_token(token: str, settings: Settings) -> dict:
    try:
        claims = jwt.decode(token, settings.secret_key, algorithms=["HS256"], options={"require": ["exp", "sub"]})
    except jwt.ExpiredSignatureError:
        raise unauthorized("Sua sessão expirou. Entre novamente.", "token_expired")
    except jwt.PyJWTError:
        raise unauthorized("Sessão inválida. Entre novamente.", "token_invalid")
    if claims.get("typ") != "access":
        raise unauthorized("Sessão inválida. Entre novamente.", "token_invalid")
    return claims


class RateLimiter:
    """Limite de tentativas em memória. Em produção com várias instâncias, troque por Redis."""

    def __init__(self) -> None:
        self._hits: Dict[str, Deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def hit(self, key: str, limit: int, window_seconds: int) -> None:
        now = time.monotonic()
        with self._lock:
            q = self._hits[key]
            while q and now - q[0] > window_seconds:
                q.popleft()
            if len(q) >= limit:
                retry = max(1, int(window_seconds - (now - q[0])) + 1)
                raise ApiError(429, "rate_limited", "Muitas tentativas. Aguarde um pouco e tente de novo.",
                               headers={"Retry-After": str(retry)})
            q.append(now)

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


limiter = RateLimiter()
