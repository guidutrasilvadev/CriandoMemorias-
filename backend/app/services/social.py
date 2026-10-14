"""Verificação dos logins do Google e do Facebook. O navegador obtém o token; o backend confere com o provedor.
Nos testes, essas funções são substituídas (monkeypatch) para não depender da internet."""
import logging
from typing import Dict

import httpx

from ..config import Settings
from ..errors import ApiError

log = logging.getLogger("cm.social")


def _not_configured(name: str) -> ApiError:
    return ApiError(503, "provider_not_configured", f"O login com {name} ainda não está configurado.")


def verify_google_id_token(id_token_value: str, s: Settings) -> Dict[str, object]:
    """Confere assinatura, validade, emissor e público (GOOGLE_CLIENT_ID) do ID token do Google."""
    if not s.google_client_id:
        raise _not_configured("Google")
    from google.auth.transport import requests as google_requests
    from google.oauth2 import id_token
    try:
        claims = id_token.verify_oauth2_token(id_token_value, google_requests.Request(), s.google_client_id)
    except ValueError:
        raise ApiError(401, "invalid_google_token", "Não foi possível validar o login com o Google. Tente de novo.")
    if claims.get("iss") not in ("accounts.google.com", "https://accounts.google.com"):
        raise ApiError(401, "invalid_google_token", "Não foi possível validar o login com o Google. Tente de novo.")
    return {"sub": str(claims["sub"]), "email": claims.get("email"),
            "email_verified": bool(claims.get("email_verified")), "name": claims.get("name") or ""}


def _http_client() -> httpx.Client:
    return httpx.Client(timeout=10)


def verify_facebook_token(access_token: str, s: Settings) -> Dict[str, object]:
    """Confere o token na Graph API (debug_token: válido, emitido para o nosso app) e lê o perfil."""
    if not (s.facebook_app_id and s.facebook_app_secret):
        raise _not_configured("Facebook")
    bad = ApiError(401, "invalid_facebook_token", "Não foi possível validar o login com o Facebook. Tente de novo.")
    try:
        with _http_client() as c:
            dbg = c.get("https://graph.facebook.com/debug_token",
                        params={"input_token": access_token,
                                "access_token": f"{s.facebook_app_id}|{s.facebook_app_secret}"})
            data = (dbg.json() or {}).get("data") or {}
            if dbg.status_code != 200 or not data.get("is_valid") or str(data.get("app_id")) != s.facebook_app_id:
                raise bad
            me = c.get("https://graph.facebook.com/me", params={"fields": "id,name,email", "access_token": access_token})
            profile = me.json() or {}
    except httpx.HTTPError as exc:
        log.warning("Facebook inacessível: %s", exc.__class__.__name__)
        raise ApiError(502, "provider_unreachable", "Não conseguimos falar com o Facebook agora. Tente em instantes.")
    except ValueError:
        raise bad
    if me.status_code != 200 or str(profile.get("id")) != str(data.get("user_id")):
        raise bad
    # e-mail do Facebook não é tratado como verificado: não vincula a contas existentes automaticamente
    return {"sub": str(profile["id"]), "email": profile.get("email"), "email_verified": False,
            "name": profile.get("name") or ""}
