"""Administração, formato de erros, CORS, cabeçalhos de segurança, limite de tentativas e configuração de produção."""
import pytest
from fastapi.testclient import TestClient

from tests.conftest import PASSWORD, add_to_cart, bearer, checkout, register

ADMIN = {"X-Admin-Key": "admin-teste"}


# ---------- administração ----------
def test_admin_requires_key(client, make_client):
    assert client.get("/admin/products").status_code == 401
    assert client.get("/admin/products", headers={"X-Admin-Key": "errada"}).json()["error"]["code"] == "admin_unauthorized"
    assert client.get("/admin/orders", headers=ADMIN).status_code == 200
    off = make_client(ADMIN_API_KEY="")
    r = off.get("/admin/products", headers={"X-Admin-Key": ""})
    assert r.status_code == 503 and r.json()["error"]["code"] == "admin_disabled"


def test_admin_product_crud(client):
    new = {"name": "Festa Unicórnio", "type": "kit", "occasion": "Festa infantil", "theme": "Fantasia e princesas",
           "price_cents": 8990, "featured": True, "file_key": "kits/unicornio.zip"}
    r = client.post("/admin/products", json=new, headers=ADMIN)
    assert r.status_code == 201
    p = r.json()
    assert p["slug"] == "festa-unicornio" and p["demo"] is False and p["active"] is True and p["file_key"]
    assert client.get("/products/festa-unicornio").status_code == 200
    assert client.get("/products", params={"q": "unicornio"}).json()["total"] == 1

    assert client.post("/admin/products", json=new, headers=ADMIN).json()["error"]["code"] == "slug_in_use"
    assert client.post("/admin/products", json={**new, "name": "Outro", "type": "inexistente"},
                       headers=ADMIN).json()["error"]["code"] == "invalid_type"
    assert client.post("/admin/products", json={**new, "price_cents": 0}, headers=ADMIN).status_code == 422

    patched = client.patch(f"/admin/products/{p['id']}", json={"price_cents": 9990, "name": "Festa Unicórnio Mágico"},
                           headers=ADMIN).json()
    assert patched["price_cents"] == 9990
    assert client.get("/products", params={"q": "magico"}).json()["total"] == 1  # a busca acompanha o novo nome

    assert client.delete(f"/admin/products/{p['id']}", headers=ADMIN).status_code == 204
    assert client.get("/products/festa-unicornio").status_code == 404
    listed = client.get("/admin/products", headers=ADMIN).json()
    assert any(x["id"] == p["id"] and x["active"] is False for x in listed)
    assert client.patch("/admin/products/9999", json={"name": "x" * 3}, headers=ADMIN).status_code == 404


def test_admin_import_upserts(client):
    rows = [{"id": 1, "name": "Festa Abelhinha", "type": "kit", "occasion": "Festa infantil", "theme": "Jardim e natureza",
             "price_cents": 6990, "demo": False},
            {"name": "Kit Novo", "type": "molde", "occasion": "Datas comemorativas", "theme": "Outros temas",
             "price_cents": 1990}]
    out = client.post("/admin/products/import", json=rows, headers=ADMIN).json()
    assert [p["name"] for p in out] == ["Festa Abelhinha", "Kit Novo"]
    assert client.get("/products/1").json()["price_cents"] == 6990 and client.get("/products/1").json()["demo"] is False
    assert client.get("/products/kit-novo").json()["type_label"] == "Arquivo digital de molde"
    assert client.get("/products/facets").json()["total"] == 38


def test_demo_products_blocked_in_production(make_client):
    """Em produção o catálogo de demonstração não vende; o catálogo real entra pela importação."""
    c = make_client(ENV="production", SECRET_KEY="x" * 40, CORS_ORIGINS="https://loja.exemplo.com",
                    PAYMENT_GATEWAY="mercadopago", MERCADOPAGO_ACCESS_TOKEN="TEST-x",
                    PUBLIC_API_URL="https://api.exemplo.com", AUTO_SEED_DEMO="true")
    t = register(c)
    add_to_cart(c, 1, bearer(t))
    r = checkout(c, t)
    assert r.status_code == 403 and r.json()["error"]["code"] == "demo_catalog"


def test_admin_orders_list_and_filter(client):
    t = register(client)
    add_to_cart(client, 1, bearer(t))
    checkout(client, t, "card")
    add_to_cart(client, 2, bearer(t))
    checkout(client, t, "pix")
    all_orders = client.get("/admin/orders", headers=ADMIN).json()
    assert len(all_orders) == 2 and all_orders[0]["payer_cpf_masked"] == "***.982.247-**"
    assert "cpf" not in str(all_orders).lower().replace("payer_cpf_masked", "")  # CPF completo nunca sai
    paid = client.get("/admin/orders", params={"status": "paid"}, headers=ADMIN).json()
    assert len(paid) == 1 and paid[0]["payment_method"] == "card"
    assert client.get("/admin/orders", params={"status": "xx"}, headers=ADMIN).status_code == 422
    assert client.post("/admin/orders/nao-existe/reconcile", headers=ADMIN).status_code == 404


def test_full_cpf_is_never_stored(client):
    import sqlite3
    t = register(client)
    add_to_cart(client, 1, bearer(t))
    checkout(client, t)
    from app.config import get_settings
    db_path = get_settings().database_url.replace("sqlite:///", "")
    con = sqlite3.connect(db_path)
    try:
        dump = "\n".join(con.iterdump())
    finally:
        con.close()
    assert "52998224725" not in dump and "529.982.247-25" not in dump
    assert "***.982.247-**" in dump


# ---------- erros, CORS e cabeçalhos ----------
def test_error_format(client):
    r = client.get("/rota-que-nao-existe")
    assert r.status_code == 404 and r.json() == {"error": {"code": "not_found", "message": "Rota não encontrada."}}
    assert client.delete("/health").json()["error"]["code"] == "method_not_allowed"
    v = client.post("/cart/items", json={"product_id": "abc"}).json()["error"]
    assert v["code"] == "validation_error" and "product_id" in v["fields"]


def test_unexpected_error_hides_details(client):
    client.app.add_api_route("/boom", lambda: 1 / 0)
    r = TestClient(client.app, raise_server_exceptions=False).get("/boom")
    assert r.status_code == 500 and r.json() == {"error": {"code": "internal_error", "message": "Algo deu errado. Tente de novo."}}


def test_cors(client):
    ok = client.options("/products", headers={"Origin": "http://localhost:8000", "Access-Control-Request-Method": "GET"})
    assert ok.headers["access-control-allow-origin"] == "http://localhost:8000"
    pre = client.options("/checkout", headers={"Origin": "http://localhost:8000", "Access-Control-Request-Method": "POST",
                                               "Access-Control-Request-Headers": "authorization,idempotency-key,x-cart-id"})
    assert pre.status_code == 200
    assert "access-control-allow-origin" in pre.headers
    evil = client.get("/products", headers={"Origin": "https://site-malicioso.com"})
    assert "access-control-allow-origin" not in evil.headers
    guest = client.post("/cart/items", json={"product_id": 1}, headers={"Origin": "http://localhost:8000"})
    assert "x-cart-id" in guest.headers["access-control-expose-headers"].lower()


def test_security_headers_and_no_store(client):
    r = client.get("/cart")
    assert r.headers["x-content-type-options"] == "nosniff" and r.headers["cache-control"] == "no-store"
    assert "cache-control" not in client.get("/products").headers


def test_body_size_limit(client):
    r = client.post("/auth/login", content=b"x", headers={"content-length": "5000000", "content-type": "application/json"})
    assert r.status_code == 413


def test_login_rate_limit(make_client):
    c = make_client(RATE_LIMIT_ENABLED="true")
    register(c)
    codes = [c.post("/auth/login", json={"identifier": "ana@exemplo.com", "password": "errada-errada"}).status_code
             for _ in range(8)]
    assert codes == [401] * 8
    blocked = c.post("/auth/login", json={"identifier": "ana@exemplo.com", "password": PASSWORD})
    assert blocked.status_code == 429 and blocked.json()["error"]["code"] == "rate_limited"
    assert int(blocked.headers["retry-after"]) > 0


def test_outbound_http_calls_are_not_logged(client):
    """O httpx registraria URLs com token (Facebook). Garante que fica em silêncio."""
    import logging
    assert logging.getLogger("httpx").getEffectiveLevel() >= logging.WARNING


def test_public_config_and_health(client):
    cfg = client.get("/config/public").json()
    assert cfg["payment_methods"] == ["pix", "boleto", "card"] and cfg["first_purchase_discount_percent"] == 10
    assert cfg["installments"]["max"] == 6 and cfg["login"]["google_client_id"] == "google-teste"
    assert cfg["card"] == {"provider": "simulated", "public_key": None}
    assert "secret" not in str(cfg).lower()
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/docs").status_code == 200


# ---------- configuração de produção ----------
def test_production_refuses_weak_config(make_client):
    with pytest.raises(RuntimeError) as exc:
        make_client(ENV="production", SECRET_KEY="curta")
    msg = str(exc.value)
    assert "SECRET_KEY" in msg and "CORS_ORIGINS" in msg and "PAYMENT_GATEWAY" in msg


def test_production_mercadopago_needs_token_and_public_url(make_client):
    with pytest.raises(RuntimeError) as exc:
        make_client(ENV="production", SECRET_KEY="x" * 40, CORS_ORIGINS="https://a.com", PAYMENT_GATEWAY="mercadopago")
    assert "MERCADOPAGO_ACCESS_TOKEN" in str(exc.value)


def test_invalid_discount_config(make_client):
    with pytest.raises(RuntimeError):
        make_client(FIRST_PURCHASE_DISCOUNT_PERCENT=100)


# ---------- site entregue pela API (desenvolvimento) ----------
def test_dev_serves_the_site_without_hiding_api_routes(make_client):
    c = make_client(SERVE_SITE="true")
    home = c.get("/")
    assert home.status_code == 200 and "Criando Memórias" in home.text
    assert c.get("/assets/js/app.js").status_code == 200
    assert c.get("/health").json() == {"status": "ok"}  # a API continua na frente do site
    assert c.get("/products").json()["total"] > 0
    missing = c.get("/nao-existe.html")
    assert missing.status_code == 404 and missing.json()["error"]["code"] == "not_found"


def test_site_is_not_served_unless_enabled(client):
    assert client.get("/").status_code == 404
