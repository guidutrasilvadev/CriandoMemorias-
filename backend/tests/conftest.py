"""Base dos testes: cada teste usa um banco novo, o gateway simulado e a internet desligada (login social é simulado)."""
import os

import pytest
from fastapi.testclient import TestClient

from app.db import reset_caches
from app.gateways import reset_gateways
from app.main import create_app
from app.security import limiter

CPF = "52998224725"  # CPF válido de teste
CPF_2 = "11144477735"
PASSWORD = "Senha-forte-123"

ENV_KEYS = [
    "ENV", "DATABASE_URL", "SECRET_KEY", "ACCESS_TOKEN_MINUTES", "REFRESH_TOKEN_DAYS", "CORS_ORIGINS", "TRUST_PROXY",
    "RATE_LIMIT_ENABLED", "ADMIN_API_KEY", "GOOGLE_CLIENT_ID", "FACEBOOK_APP_ID", "FACEBOOK_APP_SECRET",
    "PAYMENT_GATEWAY", "PUBLIC_API_URL", "MERCADOPAGO_ACCESS_TOKEN", "MERCADOPAGO_PUBLIC_KEY",
    "MERCADOPAGO_WEBHOOK_SECRET", "SIMULATED_WEBHOOK_SECRET", "ALLOW_DEMO_CHECKOUT", "MIN_ORDER_CENTS",
    "PIX_EXPIRATION_MINUTES", "BOLETO_DUE_DAYS", "CARD_ORDER_EXPIRATION_MINUTES", "MAX_INSTALLMENTS",
    "INTEREST_FREE_INSTALLMENTS", "MONTHLY_INTEREST_PERCENT", "MIN_INSTALLMENT_CENTS",
    "FIRST_PURCHASE_DISCOUNT_PERCENT", "FIRST_PURCHASE_DISCOUNT_MAX_CENTS", "OTP_TTL_MINUTES", "OTP_DEV_ECHO",
    "SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD", "SMTP_FROM", "TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN",
    "TWILIO_SMS_FROM", "TWILIO_WHATSAPP_FROM", "AUTO_SEED_DEMO", "SERVE_SITE",
]


@pytest.fixture()
def make_client(tmp_path, monkeypatch, request):
    """Cria um cliente de teste; aceita variáveis de ambiente extras: make_client(MAX_INSTALLMENTS="12")."""
    def factory(**extra):
        for key in ENV_KEYS:
            monkeypatch.delenv(key, raising=False)
        base = {"ENV": "dev", "DATABASE_URL": f"sqlite:///{tmp_path}/teste.db", "RATE_LIMIT_ENABLED": "false",
                "SECRET_KEY": "chave-de-teste-chave-de-teste-chave-de-teste-123", "PAYMENT_GATEWAY": "simulated",
                "ADMIN_API_KEY": "admin-teste", "GOOGLE_CLIENT_ID": "google-teste", "FACEBOOK_APP_ID": "fb-app",
                "FACEBOOK_APP_SECRET": "fb-secret", "AUTO_SEED_DEMO": "true", "SERVE_SITE": "false"}
        base.update({k: str(v) for k, v in extra.items()})
        for k, v in base.items():
            monkeypatch.setenv(k, v)
        reset_caches()
        reset_gateways()
        limiter.reset()
        client = TestClient(create_app(load_env=False), raise_server_exceptions=True)
        client.__enter__()
        request.addfinalizer(lambda: client.__exit__(None, None, None))
        return client
    return factory


@pytest.fixture()
def client(make_client):
    return make_client()


# ---------- ajudantes ----------
def bearer(tokens: dict) -> dict:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def register(client, email="ana@exemplo.com", name="Ana Souza", password=PASSWORD, phone=None) -> dict:
    body = {"name": name, "password": password}
    if email:
        body["email"] = email
    if phone:
        body["phone"] = phone
    r = client.post("/auth/register", json=body)
    assert r.status_code == 201, r.text
    return r.json()


def payer(cpf=CPF, **over) -> dict:
    data = {"name": "Ana Souza", "email": "ana@exemplo.com", "cpf": cpf, "phone": "11987654321"}
    data.update(over)
    return data


ADDRESS = {"zip_code": "01310-100", "street": "Avenida Paulista", "number": "1000", "neighborhood": "Bela Vista",
           "city": "São Paulo", "state": "SP"}


def add_to_cart(client, product_id, headers=None):
    r = client.post("/cart/items", json={"product_id": product_id}, headers=headers or {})
    assert r.status_code == 200, r.text
    return r.json()


def checkout(client, tokens, method="pix", cpf=CPF, key=None, **over):
    body = {"payment_method": method, "payer": payer(cpf)}
    if method == "boleto":
        body["payer"]["address"] = ADDRESS
    if method == "card":
        body.update({"card_token": "tok_approved", "card_brand": "visa", "installments": 1})
    body.update(over)
    headers = bearer(tokens)
    if key:
        headers["Idempotency-Key"] = key
    return client.post("/checkout", json=body, headers=headers)
