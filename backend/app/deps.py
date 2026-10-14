"""Dependências comuns dos endpoints: usuário logado, administrador, IP do cliente e limite de tentativas."""
import hmac
from typing import Callable, Optional

from fastapi import Depends, Header, Request
from sqlalchemy.orm import Session

from .config import Settings, get_settings
from .db import get_db
from .errors import ApiError, unauthorized
from .models import User
from .security import decode_access_token, limiter


def client_ip(request: Request, s: Settings) -> str:
    if s.trust_proxy:  # atrás de proxy/CDN confiável: usa o primeiro IP de X-Forwarded-For
        fwd = request.headers.get("x-forwarded-for", "")
        if fwd:
            return fwd.split(",")[0].strip()
    return request.client.host if request.client else "desconhecido"


def current_user_optional(authorization: Optional[str] = Header(None), db: Session = Depends(get_db),
                          s: Settings = Depends(get_settings)) -> Optional[User]:
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise unauthorized("Sessão inválida. Entre novamente.", "token_invalid")
    claims = decode_access_token(token.strip(), s)
    user = db.get(User, claims["sub"])
    if user is None or not user.is_active:
        raise unauthorized("Conta indisponível.", "account_disabled")
    return user


def current_user(user: Optional[User] = Depends(current_user_optional)) -> User:
    if user is None:
        raise unauthorized()
    return user


def require_admin(x_admin_key: Optional[str] = Header(None, alias="X-Admin-Key"),
                  s: Settings = Depends(get_settings)) -> None:
    if not s.admin_api_key:
        raise ApiError(503, "admin_disabled", "A área administrativa está desativada (ADMIN_API_KEY não definido).")
    if not x_admin_key or not hmac.compare_digest(x_admin_key.encode(), s.admin_api_key.encode()):
        raise ApiError(401, "admin_unauthorized", "Chave administrativa inválida.")


def rate_limit(name: str, limit: int, window_seconds: int) -> Callable:
    """Cria uma dependência que limita chamadas por IP (ex.: rate_limit("login", 10, 900))."""
    def dep(request: Request, s: Settings = Depends(get_settings)) -> None:
        if s.rate_limit_enabled:
            limiter.hit(f"{name}:{client_ip(request, s)}", limit, window_seconds)
    return dep
