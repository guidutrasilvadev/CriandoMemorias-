"""Compra de ponta a ponta com o gateway simulado: Pix, boleto, cartão, desconto, webhooks, expiração."""
import json
from datetime import timedelta

from app import timeutil
from tests.conftest import ADDRESS, CPF, CPF_2, add_to_cart, bearer, checkout, payer, register


def buyer(client, email="ana@exemplo.com", name="Ana Souza", product_ids=(1,)):
    t = register(client, email, name)
    for pid in product_ids:
        add_to_cart(client, pid, bearer(t))
    return t


# ---------- regras de entrada ----------
def test_checkout_requires_login_and_items(client):
    r = client.post("/checkout", json={"payment_method": "pix", "payer": payer()})
    assert r.status_code == 401
    t = register(client)
    r = checkout(client, t)
    assert r.status_code == 400 and r.json()["error"]["code"] == "cart_empty"


def test_checkout_validation(client):
    t = buyer(client)
    bad_cpf = checkout(client, t, cpf="11111111111")
    assert bad_cpf.status_code == 422 and "payer.cpf" in bad_cpf.json()["error"]["fields"]
    one_name = client.post("/checkout", headers=bearer(t), json={"payment_method": "pix", "payer": payer(name="Ana")})
    assert one_name.status_code == 422
    no_addr = client.post("/checkout", headers=bearer(t), json={"payment_method": "boleto", "payer": payer()})
    assert no_addr.status_code == 422
    no_token = client.post("/checkout", headers=bearer(t), json={"payment_method": "card", "payer": payer()})
    assert no_token.status_code == 422
    bad_cep = payer()
    bad_cep["address"] = {**ADDRESS, "zip_code": "123"}
    assert client.post("/checkout", headers=bearer(t), json={"payment_method": "boleto", "payer": bad_cep}).status_code == 422
    assert client.post("/checkout", headers={**bearer(t), "Idempotency-Key": "curta"},
                       json={"payment_method": "pix", "payer": payer()}).json()["error"]["code"] == "invalid_idempotency_key"


def test_demo_catalog_cannot_be_bought_when_disallowed(make_client):
    c = make_client(ALLOW_DEMO_CHECKOUT="false")
    t = buyer(c)
    r = checkout(c, t)
    assert r.status_code == 403 and r.json()["error"]["code"] == "demo_catalog"


def test_minimum_order(make_client):
    c = make_client(MIN_ORDER_CENTS=900000)
    t = buyer(c)
    r = checkout(c, t)
    assert r.status_code == 400 and r.json()["error"]["code"] == "order_too_small"
    assert "R$ 9.000,00" in r.json()["error"]["message"]


def test_prices_come_from_the_database_not_the_client(client):
    t = buyer(client)
    r = client.post("/checkout", headers=bearer(t), json={"payment_method": "pix", "payer": payer(),
                                                           "total_cents": 1, "price_cents": 1})
    assert r.status_code == 200 and r.json()["subtotal_cents"] == 7490  # campos extras ignorados


# ---------- Pix ----------
def test_pix_flow_with_first_purchase_discount(client):
    t = buyer(client, product_ids=(1, 2))
    r = checkout(client, t, "pix")
    assert r.status_code == 200, r.text
    o = r.json()
    assert o["status"] == "pending" and o["payment_method"] == "pix" and o["code"].startswith("CM-")
    assert (o["subtotal_cents"], o["discount_cents"], o["total_cents"]) == (14980, 1498, 13482)
    assert o["discount_code"] == "PRIMEIRA_COMPRA" and o["charged_cents"] == 13482
    pay = o["payment"]
    assert pay["status"] == "pending" and pay["amount_cents"] == 13482 and pay["installments"] == 1
    assert pay["pix"]["qr_code"].startswith("00020126") and pay["pix"]["expires_at"].endswith("Z")
    assert pay["boleto"] is None
    assert [i["name"] for i in o["items"]] == ["Festa Abelhinha", "Festa Margarida"]

    # acompanhar pelo pedido: ainda pendente
    got = client.get(f"/orders/{o['id']}", headers=bearer(t)).json()
    assert got["status"] == "pending"
    # o carrinho só esvazia quando paga
    assert client.get("/cart", headers=bearer(t)).json()["items_count"] == 2

    paid = client.post(f"/dev/orders/{o['id']}/approve").json()
    assert paid["status"] == "paid" and paid["paid_at"].endswith("Z") and paid["payment"]["status"] == "approved"
    assert client.get("/cart", headers=bearer(t)).json()["items_count"] == 0

    lib = client.get("/me/library", headers=bearer(t)).json()
    assert [x["product"]["name"] for x in lib] == ["Festa Abelhinha", "Festa Margarida"]
    assert lib[0]["order_code"] == o["code"] and lib[0]["download_available"] is False
    assert [x["code"] for x in client.get("/orders", headers=bearer(t)).json()] == [o["code"]]


def test_second_purchase_has_no_discount(client):
    t = buyer(client)
    first = checkout(client, t).json()
    client.post(f"/dev/orders/{first['id']}/approve")
    add_to_cart(client, 2, bearer(t))
    second = checkout(client, t).json()
    assert second["discount_cents"] == 0 and second["discount_code"] is None and second["total_cents"] == 7490


def test_unpaid_orders_do_not_use_up_the_discount(client):
    t = buyer(client)
    first = checkout(client, t).json()
    assert first["discount_cents"] == 749
    client.post(f"/dev/orders/{first['id']}/expire")
    again = checkout(client, t).json()
    assert again["discount_cents"] == 749  # a primeira não foi paga


def test_discount_is_per_cpf_not_just_per_account(client):
    a = buyer(client, "a@exemplo.com", "Ana Alves")
    first = checkout(client, a, cpf=CPF).json()
    client.post(f"/dev/orders/{first['id']}/approve")
    b = buyer(client, "b@exemplo.com", "Bia Barros")  # conta nova, mesmo CPF
    same_cpf = checkout(client, b, cpf=CPF).json()
    assert same_cpf["discount_cents"] == 0
    other = checkout(client, b, cpf=CPF_2).json()  # CPF diferente: elegível (limite conhecido: não impede CPFs distintos)
    assert other["discount_cents"] == 749


def test_discount_disabled(make_client):
    c = make_client(FIRST_PURCHASE_DISCOUNT_PERCENT=0)
    t = buyer(c)
    o = checkout(c, t).json()
    assert o["discount_cents"] == 0 and o["discount_code"] is None


def test_new_checkout_cancels_previous_pending_order(client):
    t = buyer(client)
    first = checkout(client, t, "pix").json()
    second = checkout(client, t, "boleto").json()
    assert client.get(f"/orders/{first['id']}", headers=bearer(t)).json()["status"] == "canceled"
    assert second["status"] == "pending" and second["payment"]["boleto"] is not None


def test_idempotency_key_returns_same_order(client):
    t = buyer(client)
    a = checkout(client, t, key="tentativa-0001").json()
    b = checkout(client, t, key="tentativa-0001").json()
    assert a["id"] == b["id"] and a["payment"]["id"] == b["payment"]["id"]
    assert len(client.get("/orders", headers=bearer(t)).json()) == 1
    c = checkout(client, t, key="tentativa-0002").json()
    assert c["id"] != a["id"]


# ---------- boleto ----------
def test_boleto_flow(client):
    t = buyer(client)
    o = checkout(client, t, "boleto").json()
    b = o["payment"]["boleto"]
    assert len("".join(ch for ch in b["digitable_line"] if ch.isdigit())) == 47
    assert b["url"].startswith("https://") and b["barcode"] and o["payment"]["pix"] is None
    due = (timeutil.utcnow() - timedelta(hours=3) + timedelta(days=3)).date().isoformat()
    assert b["due_date"] == due
    assert client.post(f"/dev/orders/{o['id']}/approve").json()["status"] == "paid"


# ---------- cartão ----------
def test_card_approved_with_installments(client):
    t = buyer(client)
    r = checkout(client, t, "card", installments=3)
    o = r.json()
    assert r.status_code == 200 and o["status"] == "paid" and o["installments"] == 3
    assert o["payment"]["status"] == "approved" and o["payment"]["installments"] == 3
    assert o["payment"]["total_paid_cents"] == o["charged_cents"] == o["total_cents"] == 6741
    assert client.get("/cart", headers=bearer(t)).json()["items_count"] == 0


def test_card_rejected_keeps_cart_and_allows_retry(client):
    t = buyer(client)
    o = checkout(client, t, "card", card_token="tok_rejected").json()
    assert o["status"] == "failed" and o["payment"]["status"] == "rejected"
    assert o["payment"]["status_detail"] == "cc_rejected_insufficient_amount"
    assert client.get("/cart", headers=bearer(t)).json()["items_count"] == 1
    retry = checkout(client, t, "card", card_token="tok_approved").json()
    assert retry["status"] == "paid" and retry["discount_cents"] == 749  # recusa não gasta o desconto


def test_card_pending_review_then_approved(client):
    t = buyer(client)
    o = checkout(client, t, "card", card_token="tok_pending").json()
    assert o["status"] == "pending" and o["payment"]["status"] == "pending"
    assert client.post(f"/dev/orders/{o['id']}/approve").json()["status"] == "paid"


def test_card_invalid_token_is_a_clean_error(client):
    t = buyer(client)
    r = checkout(client, t, "card", card_token="numero-do-cartao-em-claro")
    assert r.status_code == 400 and r.json()["error"]["code"] == "payment_gateway_error"
    orders = client.get("/orders", headers=bearer(t)).json()
    assert orders[0]["status"] == "failed"  # ficou registrado


def test_invalid_installments(client):
    t = buyer(client)
    r = checkout(client, t, "card", installments=7)  # máx. padrão é 6
    assert r.status_code == 400 and r.json()["error"]["code"] == "invalid_installments"
    assert client.get("/orders", headers=bearer(t)).json() == []  # nada foi criado


def test_installments_with_interest_are_charged_with_interest(make_client):
    c = make_client(FIRST_PURCHASE_DISCOUNT_PERCENT=0, MAX_INSTALLMENTS=6, INTEREST_FREE_INSTALLMENTS=2,
                    MONTHLY_INTEREST_PERCENT=2)
    t = buyer(c)
    options = c.get("/cart", headers=bearer(t)).json()["installment_options"]
    expected = next(x for x in options if x["installments"] == 6)
    o = checkout(c, t, "card", installments=6).json()
    assert o["total_cents"] == 7490 and o["charged_cents"] == expected["total_cents"] > 7490
    assert o["payment"]["amount_cents"] == 7490 and o["payment"]["total_paid_cents"] == expected["total_cents"]
    add_to_cart(c, 1, bearer(t))  # o carrinho esvaziou ao pagar
    free = checkout(c, t, "card", installments=2).json()
    assert free["charged_cents"] == 7490


def test_pix_and_boleto_ignore_installments(client):
    t = buyer(client)
    o = checkout(client, t, "pix", installments=6).json()
    assert o["installments"] == 1 and o["payment"]["installments"] == 1


def test_installments_endpoint(client):
    r = client.get("/payments/installments", params={"amount_cents": 7490}).json()
    assert [o["installments"] for o in r] == [1, 2, 3, 4, 5, 6]
    assert r[2] == {"installments": 3, "installment_cents": 2497, "total_cents": 7490, "interest_free": True}
    assert client.get("/payments/installments", params={"amount_cents": 0}).status_code == 422
    assert len(client.get("/payments/installments", params={"amount_cents": 1500}).json()) == 3


# ---------- cancelar, ver pedidos de outros, expirar ----------
def test_cancel_order(client):
    t = buyer(client)
    o = checkout(client, t).json()
    c = client.post(f"/orders/{o['id']}/cancel", headers=bearer(t))
    assert c.status_code == 200 and c.json()["status"] == "canceled" and c.json()["payment"]["status"] == "cancelled"
    again = client.post(f"/orders/{o['id']}/cancel", headers=bearer(t))
    assert again.status_code == 409 and again.json()["error"]["code"] == "order_not_cancelable"
    # quem já pagou não cancela por aqui
    paid = checkout(client, t, "card").json()
    assert client.post(f"/orders/{paid['id']}/cancel", headers=bearer(t)).status_code == 409


def test_other_user_cannot_see_or_cancel_order(client):
    a = buyer(client, "a@exemplo.com", "Ana Alves")
    o = checkout(client, a).json()
    b = register(client, "b@exemplo.com", "Bia Barros")
    assert client.get(f"/orders/{o['id']}", headers=bearer(b)).status_code == 404
    assert client.post(f"/orders/{o['id']}/cancel", headers=bearer(b)).status_code == 404
    assert client.get("/orders", headers=bearer(b)).json() == []
    assert client.get("/orders/inexistente", headers=bearer(a)).status_code == 404


def test_pix_expires_lazily(client, monkeypatch):
    t = buyer(client)
    o = checkout(client, t).json()
    real = timeutil.utcnow
    monkeypatch.setattr(timeutil, "utcnow", lambda: real() + timedelta(minutes=45))
    got = client.get(f"/orders/{o['id']}", headers=bearer(t)).json()
    assert got["status"] == "expired" and got["payment"]["status"] == "expired"
    assert client.get("/cart", headers=bearer(t)).json()["items_count"] == 1  # carrinho preservado


def test_late_payment_after_expiry_still_delivers(client, monkeypatch):
    """Cliente pagou o Pix no último segundo e o aviso chegou depois de expirarmos: o dinheiro entrou, o kit é dele."""
    t = buyer(client)
    o = checkout(client, t).json()
    real = timeutil.utcnow
    monkeypatch.setattr(timeutil, "utcnow", lambda: real() + timedelta(minutes=45))
    assert client.get(f"/orders/{o['id']}", headers=bearer(t)).json()["status"] == "expired"
    assert client.post(f"/dev/orders/{o['id']}/approve").json()["status"] == "paid"
    assert len(client.get("/me/library", headers=bearer(t)).json()) == 1


def test_boleto_has_grace_period(client, monkeypatch):
    t = buyer(client)
    o = checkout(client, t, "boleto").json()
    real = timeutil.utcnow
    monkeypatch.setattr(timeutil, "utcnow", lambda: real() + timedelta(days=4))  # venceu ontem, ainda na tolerância
    assert client.get(f"/orders/{o['id']}", headers=bearer(t)).json()["status"] == "pending"
    monkeypatch.setattr(timeutil, "utcnow", lambda: real() + timedelta(days=7))
    assert client.get(f"/orders/{o['id']}", headers=bearer(t)).json()["status"] == "expired"


def test_refund_removes_from_library(client):
    from app.gateways import get_gateway
    t = buyer(client)
    o = checkout(client, t, "card").json()
    assert len(client.get("/me/library", headers=bearer(t)).json()) == 1
    gw = get_gateway()
    pid = o["payment"]["id"]
    from app.db import get_sessionmaker
    from app.models import Payment
    with get_sessionmaker()() as db:
        provider_id = db.get(Payment, pid).provider_payment_id
    gw.set_status(provider_id, "refunded")
    body = json.dumps({"payment_id": provider_id, "status": "refunded"}).encode()
    r = client.post("/webhooks/simulated", content=body, headers={"x-signature": gw.sign(body)})
    assert r.status_code == 200 and r.json()["status"] == "refunded"
    assert client.get("/me/library", headers=bearer(t)).json() == []
    # e a primeira compra continua "gasta": reembolso não devolve o direito ao desconto
    add_to_cart(client, 2, bearer(t))
    assert checkout(client, t).json()["discount_cents"] == 0


# ---------- webhooks ----------
def webhook(client, gw, provider_id, status, sign=True, bad=False):
    body = json.dumps({"payment_id": provider_id, "status": status}).encode()
    sig = "0" * 64 if bad else gw.sign(body)
    return client.post("/webhooks/simulated", content=body, headers={"x-signature": sig} if sign else {})


def provider_id(order):
    from app.db import get_sessionmaker
    from app.models import Payment
    with get_sessionmaker()() as db:
        return db.get(Payment, order["payment"]["id"]).provider_payment_id


def test_webhook_approves_order(client):
    from app.gateways import get_gateway
    t = buyer(client)
    o = checkout(client, t).json()
    r = webhook(client, get_gateway(), provider_id(o), "approved")
    assert r.status_code == 200 and r.json() == {"received": True, "order": o["code"], "status": "paid"}
    assert client.get(f"/orders/{o['id']}", headers=bearer(t)).json()["status"] == "paid"
    # repetir o mesmo aviso é inofensivo
    again = webhook(client, get_gateway(), provider_id(o), "approved")
    assert again.status_code == 200 and again.json()["status"] == "paid"
    assert len(client.get("/me/library", headers=bearer(t)).json()) == 1


def test_webhook_rejects_bad_signature_and_unknown_payment(client):
    from app.gateways import get_gateway
    t = buyer(client)
    o = checkout(client, t).json()
    gw = get_gateway()
    assert webhook(client, gw, provider_id(o), "approved", bad=True).status_code == 401
    assert webhook(client, gw, provider_id(o), "approved", sign=False).status_code == 401
    assert client.get(f"/orders/{o['id']}", headers=bearer(t)).json()["status"] == "pending"  # nada mudou
    unknown = webhook(client, gw, "sim_inexistente", "approved")
    assert unknown.status_code == 404 and unknown.json()["error"]["code"] == "payment_unknown"
    assert client.post("/webhooks/mercadopago", content=b"{}").status_code == 404  # só o gateway ativo recebe


def test_approved_payment_never_goes_back(client):
    from app.gateways import get_gateway
    t = buyer(client)
    o = checkout(client, t).json()
    gw = get_gateway()
    webhook(client, gw, provider_id(o), "approved")
    late = webhook(client, gw, provider_id(o), "rejected")
    assert late.json()["status"] == "paid"
    assert client.get(f"/orders/{o['id']}", headers=bearer(t)).json()["payment"]["status"] == "approved"


def test_dev_simulator_is_off_in_production(make_client):
    c = make_client(ENV="production", SECRET_KEY="x" * 40,
                    CORS_ORIGINS="https://loja.exemplo.com", PAYMENT_GATEWAY="mercadopago",
                    MERCADOPAGO_ACCESS_TOKEN="TEST-x", PUBLIC_API_URL="https://api.exemplo.com", AUTO_SEED_DEMO="false")
    assert c.post("/dev/orders/abc/approve").status_code == 404
    assert c.get("/docs").status_code == 404 and c.get("/openapi.json").status_code == 404


# ---------- "o que a pessoa viu é o que ela paga" ----------
def test_expected_total_guards_against_a_price_that_changed(client):
    a = buyer(client, "a@exemplo.com", "Ana Alves")
    first = checkout(client, a, cpf=CPF).json()
    client.post(f"/dev/orders/{first['id']}/approve")
    b = buyer(client, "b@exemplo.com", "Bia Barros")  # conta nova com o mesmo CPF: o carrinho mostra 10%, o servidor não dá
    assert client.get("/cart", headers=bearer(b)).json()["total_cents"] == 6741
    r = checkout(client, b, "card", cpf=CPF, expected_total_cents=6741)
    err = r.json()["error"]
    assert r.status_code == 409 and err["code"] == "price_changed"
    assert err["details"] == {"total_cents": 7490, "charged_cents": 7490, "discount_cents": 0, "discount_code": None}
    assert "R$" in err["message"] and "7,49" not in err["message"] and "74,90" in err["message"]
    assert client.get("/orders", headers=bearer(b)).json() == []  # nada criado, nada cobrado
    assert client.get("/cart", headers=bearer(b)).json()["items_count"] == 1  # carrinho intacto
    ok = checkout(client, b, "card", cpf=CPF, expected_total_cents=7490)  # confirmou o valor novo
    assert ok.status_code == 200 and ok.json()["status"] == "paid" and ok.json()["charged_cents"] == 7490


def test_expected_total_matches_the_installment_total(make_client):
    c = make_client(FIRST_PURCHASE_DISCOUNT_PERCENT=0, MAX_INSTALLMENTS=6, INTEREST_FREE_INSTALLMENTS=2, MONTHLY_INTEREST_PERCENT=2)
    t = buyer(c)
    options = c.get("/cart", headers=bearer(t)).json()["installment_options"]
    six = next(x for x in options if x["installments"] == 6)
    assert checkout(c, t, "card", installments=6, expected_total_cents=7490).status_code == 409  # sem juros: valor errado
    assert checkout(c, t, "card", installments=6, expected_total_cents=six["total_cents"]).status_code == 200


def test_expected_total_is_optional(client):
    t = buyer(client)
    assert checkout(client, t, "pix").status_code == 200
