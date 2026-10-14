"""Login: e-mail/telefone com senha, código (OTP), Google, Facebook, sessões e benefícios."""
import httpx

from app.services import social
from tests.conftest import PASSWORD, bearer, register


# ---------- senha ----------
def test_register_login_me(client):
    t = register(client, "ana@exemplo.com", "Ana Souza")
    assert t["is_new_user"] is True and t["token_type"] == "bearer" and t["expires_in"] == 900
    assert t["user"]["email"] == "ana@exemplo.com" and t["user"]["has_password"] is True
    assert t["first_purchase_discount"]["status"] == "eligible" and t["first_purchase_discount"]["percent"] == 10

    r = client.post("/auth/login", json={"identifier": "Ana@Exemplo.com", "password": PASSWORD})
    assert r.status_code == 200 and r.json()["is_new_user"] is False
    me = client.get("/me", headers=bearer(r.json()))
    assert me.status_code == 200 and me.json()["name"] == "Ana Souza"


def test_register_with_phone_and_login_by_phone(client):
    register(client, email=None, name="Bia Lima", phone="(11) 98765-4321")
    r = client.post("/auth/login", json={"identifier": "11987654321", "password": PASSWORD})
    assert r.status_code == 200 and r.json()["user"]["phone"] == "+5511987654321"


def test_register_validation(client):
    assert client.post("/auth/register", json={"name": "A", "password": "curta"}).status_code == 422
    r = client.post("/auth/register", json={"name": "Ana", "password": PASSWORD})  # sem e-mail nem telefone
    assert r.status_code == 422 and r.json()["error"]["code"] == "validation_error"
    r = client.post("/auth/register", json={"name": "Ana", "email": "invalido", "password": PASSWORD})
    assert r.status_code == 422 and "email" in r.json()["error"]["fields"]


def test_duplicate_email(client):
    register(client)
    r = client.post("/auth/register", json={"name": "Outra", "email": "ANA@exemplo.com", "password": PASSWORD})
    assert r.status_code == 409 and r.json()["error"]["code"] == "account_exists"


def test_wrong_password_and_unknown_account_look_the_same(client):
    register(client)
    a = client.post("/auth/login", json={"identifier": "ana@exemplo.com", "password": "errada-errada"})
    b = client.post("/auth/login", json={"identifier": "ninguem@exemplo.com", "password": "errada-errada"})
    assert a.status_code == b.status_code == 401 and a.json() == b.json()
    assert a.json()["error"]["code"] == "invalid_credentials"


def test_bad_token_rejected(client):
    assert client.get("/me").status_code == 401
    assert client.get("/me", headers={"Authorization": "Bearer lixo"}).json()["error"]["code"] == "token_invalid"
    assert client.get("/me", headers={"Authorization": "Basic abc"}).status_code == 401


def test_access_token_expires(make_client):
    c = make_client(ACCESS_TOKEN_MINUTES=0)
    t = register(c)
    r = c.get("/me", headers=bearer(t))
    assert r.status_code == 401 and r.json()["error"]["code"] == "token_expired"


# ---------- refresh / logout ----------
def test_refresh_rotation_and_reuse_detection(client):
    t = register(client)
    r1 = client.post("/auth/refresh", json={"refresh_token": t["refresh_token"]})
    assert r1.status_code == 200
    t2 = r1.json()
    assert t2["refresh_token"] != t["refresh_token"]
    assert client.get("/me", headers=bearer(t2)).status_code == 200
    # reaproveitar o token antigo derruba todas as sessões da conta
    r2 = client.post("/auth/refresh", json={"refresh_token": t["refresh_token"]})
    assert r2.status_code == 401 and r2.json()["error"]["code"] == "token_reused"
    assert client.post("/auth/refresh", json={"refresh_token": t2["refresh_token"]}).status_code == 401


def test_logout_revokes_refresh(client):
    t = register(client)
    assert client.post("/auth/logout", json={"refresh_token": t["refresh_token"]}).status_code == 204
    assert client.post("/auth/refresh", json={"refresh_token": t["refresh_token"]}).status_code == 401


def test_update_profile(client):
    t = register(client)
    r = client.patch("/me", json={"name": "  Ana   Maria  "}, headers=bearer(t))
    assert r.status_code == 200 and r.json()["name"] == "Ana Maria"


# ---------- código (OTP) ----------
def ask_code(client, destination, channel, **extra):
    return client.post("/auth/otp/request", json={"destination": destination, "channel": channel, **extra})


def test_otp_sms_creates_account_and_logs_in(client):
    r = ask_code(client, "(11) 98765-4321", "sms")
    assert r.status_code == 200 and r.json()["sent"] is True
    code = r.json()["dev_code"]
    v = client.post("/auth/otp/verify", json={"destination": "11987654321", "code": code, "name": "Carla"})
    assert v.status_code == 200
    body = v.json()
    assert body["is_new_user"] is True and body["user"]["phone"] == "+5511987654321"
    assert body["user"]["phone_verified"] is True and body["user"]["has_password"] is False
    # o mesmo código não vale duas vezes
    again = client.post("/auth/otp/verify", json={"destination": "11987654321", "code": code})
    assert again.status_code == 400 and again.json()["error"]["code"] == "otp_invalid"


def test_otp_email_existing_user(client):
    register(client, "ana@exemplo.com")
    code = ask_code(client, "ana@exemplo.com", "email").json()["dev_code"]
    v = client.post("/auth/otp/verify", json={"destination": "ana@exemplo.com", "code": code})
    assert v.status_code == 200 and v.json()["is_new_user"] is False and v.json()["user"]["email_verified"] is True


def test_otp_wrong_code_and_attempt_limit(client):
    code = ask_code(client, "11987654321", "whatsapp").json()["dev_code"]
    wrong = "000000" if code != "000000" else "111111"
    r = client.post("/auth/otp/verify", json={"destination": "11987654321", "code": wrong})
    assert r.status_code == 400 and r.json()["error"]["code"] == "otp_wrong"
    for _ in range(5):
        client.post("/auth/otp/verify", json={"destination": "11987654321", "code": wrong})
    # estourou as tentativas: nem o código certo vale mais
    ok = client.post("/auth/otp/verify", json={"destination": "11987654321", "code": code})
    assert ok.status_code == 400 and ok.json()["error"]["code"] == "otp_invalid"


def test_otp_cooldown_and_validation(client):
    assert ask_code(client, "ana@exemplo.com", "email").status_code == 200
    r = ask_code(client, "ana@exemplo.com", "email")
    assert r.status_code == 429 and r.json()["error"]["code"] == "otp_cooldown" and "Retry-After" in r.headers
    assert ask_code(client, "nao-e-email", "email").status_code == 400
    assert ask_code(client, "123", "sms").status_code == 400
    assert client.post("/auth/otp/verify", json={"destination": "ana@exemplo.com", "code": "12ab"}).status_code == 422


def test_otp_new_code_invalidates_old(client, monkeypatch):
    from app import timeutil
    first = ask_code(client, "11987654321", "sms").json()["dev_code"]
    real = timeutil.utcnow
    from datetime import timedelta
    monkeypatch.setattr(timeutil, "utcnow", lambda: real() + timedelta(seconds=120))
    second = ask_code(client, "11987654321", "sms").json()["dev_code"]
    if first != second:
        assert client.post("/auth/otp/verify", json={"destination": "11987654321", "code": first}).status_code == 400
    assert client.post("/auth/otp/verify", json={"destination": "11987654321", "code": second}).status_code == 200


def test_otp_link_phone_to_logged_user(client):
    t = register(client, "ana@exemplo.com")
    assert ask_code(client, "11987654321", "sms", purpose="link").status_code == 401  # precisa estar logada
    code = client.post("/auth/otp/request", headers=bearer(t),
                       json={"destination": "11987654321", "channel": "sms", "purpose": "link"}).json()["dev_code"]
    v = client.post("/auth/otp/verify", json={"destination": "11987654321", "code": code})
    assert v.status_code == 200 and v.json()["linked"] is True
    me = client.get("/me", headers=bearer(t)).json()
    assert me["phone"] == "+5511987654321" and me["phone_verified"] is True


def test_otp_link_rejects_contact_of_other_account(client):
    register(client, "ana@exemplo.com", phone="11987654321")
    t = register(client, "bia@exemplo.com", "Bia Lima")
    r = client.post("/auth/otp/request", headers=bearer(t),
                    json={"destination": "11987654321", "channel": "sms", "purpose": "link"})
    assert r.status_code == 409 and r.json()["error"]["code"] == "contact_in_use"


def test_otp_unavailable_in_production_without_provider(make_client):
    c = make_client(ENV="production", SECRET_KEY="x" * 40,
                    CORS_ORIGINS="https://loja.exemplo.com", PAYMENT_GATEWAY="mercadopago",
                    MERCADOPAGO_ACCESS_TOKEN="TEST-x", PUBLIC_API_URL="https://api.exemplo.com", AUTO_SEED_DEMO="true")
    r = c.post("/auth/otp/request", json={"destination": "ana@exemplo.com", "channel": "email"})
    assert r.status_code == 503 and r.json()["error"]["code"] == "otp_channel_unavailable"


# ---------- Google ----------
def google_info(sub="g-1", email="gabi@gmail.com", verified=True, name="Gabi Alves"):
    return {"sub": sub, "email": email, "email_verified": verified, "name": name}


def test_google_creates_then_reuses_account(client, monkeypatch):
    monkeypatch.setattr(social, "verify_google_id_token", lambda tok, s: google_info())
    r = client.post("/auth/google", json={"id_token": "x" * 30})
    assert r.status_code == 200
    b = r.json()
    assert b["is_new_user"] is True and b["user"]["providers"] == ["google"] and b["user"]["email_verified"] is True
    assert b["first_purchase_discount"]["status"] == "eligible"
    again = client.post("/auth/google", json={"id_token": "x" * 30}).json()
    assert again["is_new_user"] is False and again["user"]["id"] == b["user"]["id"]


def test_google_links_to_existing_verified_account(client, monkeypatch):
    t = register(client, "gabi@gmail.com", "Gabi Alves")
    code = client.post("/auth/otp/request", json={"destination": "gabi@gmail.com", "channel": "email"}).json()["dev_code"]
    client.post("/auth/otp/verify", json={"destination": "gabi@gmail.com", "code": code})  # prova o e-mail
    monkeypatch.setattr(social, "verify_google_id_token", lambda tok, s: google_info())
    r = client.post("/auth/google", json={"id_token": "x" * 30}).json()
    assert r["user"]["id"] == t["user"]["id"] and "google" in r["user"]["providers"] and r["user"]["has_password"]


def test_google_takes_over_unverified_preregistered_account(client, monkeypatch):
    """Alguém cadastrou o e-mail da Gabi sem prová-lo. Quando ela entra com o Google, a senha dessa pessoa deixa de valer."""
    attacker = register(client, "gabi@gmail.com", "Intruso", password="Senha-do-intruso-1")
    monkeypatch.setattr(social, "verify_google_id_token", lambda tok, s: google_info())
    r = client.post("/auth/google", json={"id_token": "x" * 30}).json()
    assert r["user"]["id"] == attacker["user"]["id"] and r["user"]["has_password"] is False
    assert client.post("/auth/login", json={"identifier": "gabi@gmail.com", "password": "Senha-do-intruso-1"}).status_code == 401
    assert client.post("/auth/refresh", json={"refresh_token": attacker["refresh_token"]}).status_code == 401


def test_google_unverified_email_never_links(client, monkeypatch):
    register(client, "gabi@gmail.com")
    monkeypatch.setattr(social, "verify_google_id_token", lambda tok, s: google_info(verified=False))
    r = client.post("/auth/google", json={"id_token": "x" * 30})
    assert r.status_code == 409 and r.json()["error"]["code"] == "account_exists_link_required"


def test_google_not_configured(make_client):
    c = make_client(GOOGLE_CLIENT_ID="")
    r = c.post("/auth/google", json={"id_token": "x" * 30})
    assert r.status_code == 503 and r.json()["error"]["code"] == "provider_not_configured"


def test_google_invalid_token(client):
    r = client.post("/auth/google", json={"id_token": "isto-nao-e-um-token-valido"})
    assert r.status_code == 401 and r.json()["error"]["code"] == "invalid_google_token"


# ---------- Facebook ----------
def fb_info(sub="f-1", email="fabio@exemplo.com", name="Fábio Reis"):
    return {"sub": sub, "email": email, "email_verified": False, "name": name}


def test_facebook_creates_account(client, monkeypatch):
    monkeypatch.setattr(social, "verify_facebook_token", lambda tok, s: fb_info())
    r = client.post("/auth/facebook", json={"access_token": "t" * 20})
    assert r.status_code == 200 and r.json()["user"]["providers"] == ["facebook"]
    assert r.json()["user"]["email_verified"] is False


def test_facebook_without_email(client, monkeypatch):
    monkeypatch.setattr(social, "verify_facebook_token", lambda tok, s: fb_info(email=None))
    r = client.post("/auth/facebook", json={"access_token": "t" * 20})
    assert r.status_code == 200 and r.json()["user"]["email"] is None


def test_facebook_never_auto_links_by_email_but_can_link_when_logged_in(client, monkeypatch):
    t = register(client, "fabio@exemplo.com", "Fábio Reis")
    monkeypatch.setattr(social, "verify_facebook_token", lambda tok, s: fb_info())
    r = client.post("/auth/facebook", json={"access_token": "t" * 20})
    assert r.status_code == 409 and r.json()["error"]["code"] == "account_exists_link_required"
    linked = client.post("/me/link/facebook", json={"access_token": "t" * 20}, headers=bearer(t))
    assert linked.status_code == 200 and linked.json()["providers"] == ["facebook"]
    assert client.post("/auth/facebook", json={"access_token": "t" * 20}).json()["user"]["id"] == t["user"]["id"]


def test_link_identity_belonging_to_someone_else(client, monkeypatch):
    monkeypatch.setattr(social, "verify_facebook_token", lambda tok, s: fb_info(email=None))
    client.post("/auth/facebook", json={"access_token": "t" * 20})
    other = register(client, "outra@exemplo.com", "Outra Pessoa")
    r = client.post("/me/link/facebook", json={"access_token": "t" * 20}, headers=bearer(other))
    assert r.status_code == 409 and r.json()["error"]["code"] == "identity_in_use"


def test_verify_facebook_token_calls_graph_api(make_client, monkeypatch):
    make_client()
    from app.config import get_settings
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        if request.url.path == "/debug_token":
            assert request.url.params["access_token"] == "fb-app|fb-secret"
            return httpx.Response(200, json={"data": {"is_valid": True, "app_id": "fb-app", "user_id": "123"}})
        return httpx.Response(200, json={"id": "123", "name": "Fábio Reis", "email": "fabio@exemplo.com"})

    monkeypatch.setattr(social, "_http_client", lambda: httpx.Client(transport=httpx.MockTransport(handler)))
    info = social.verify_facebook_token("tok", get_settings())
    assert info == {"sub": "123", "email": "fabio@exemplo.com", "email_verified": False, "name": "Fábio Reis"}
    assert calls == ["/debug_token", "/me"]


def test_verify_facebook_token_rejects_other_app_and_invalid(make_client, monkeypatch):
    make_client()
    from app.config import get_settings
    from app.errors import ApiError
    import pytest

    def other_app(request):
        return httpx.Response(200, json={"data": {"is_valid": True, "app_id": "OUTRO", "user_id": "1"}})

    def invalid(request):
        return httpx.Response(200, json={"data": {"is_valid": False}})

    for handler in (other_app, invalid):
        monkeypatch.setattr(social, "_http_client", lambda h=handler: httpx.Client(transport=httpx.MockTransport(h)))
        with pytest.raises(ApiError) as exc:
            social.verify_facebook_token("tok", get_settings())
        assert exc.value.code == "invalid_facebook_token"


# ---------- benefícios na tela de login ----------
def test_login_benefits(client):
    b = client.get("/auth/benefits").json()
    ids = [x["id"] for x in b["benefits"]]
    assert ids == ["first_purchase_discount", "saved_cart", "orders_library"]
    assert b["benefits"][0]["title"] == "10% de desconto na primeira compra"
    assert set(b["providers"]) == {"google", "facebook", "email", "phone"}
    assert "uma vez por pessoa" in b["fine_print"]


def test_login_benefits_without_discount_or_providers(make_client):
    c = make_client(FIRST_PURCHASE_DISCOUNT_PERCENT=0, GOOGLE_CLIENT_ID="", FACEBOOK_APP_ID="")
    b = c.get("/auth/benefits").json()
    assert [x["id"] for x in b["benefits"]] == ["saved_cart", "orders_library"]
    assert b["providers"] == ["email", "phone"] and b["fine_print"] == ""


def test_benefits_fine_print_mentions_cap(make_client):
    c = make_client(FIRST_PURCHASE_DISCOUNT_PERCENT=12.5, FIRST_PURCHASE_DISCOUNT_MAX_CENTS=2000)
    b = c.get("/auth/benefits").json()
    assert b["benefits"][0]["title"] == "12,5% de desconto na primeira compra"
    assert "limitado a R$ 20,00" in b["fine_print"]
