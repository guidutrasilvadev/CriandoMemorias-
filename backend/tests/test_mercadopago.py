"""Adaptador do Mercado Pago, com a API simulada (httpx.MockTransport). Não substitui o teste no sandbox real."""
import hashlib
import hmac
import json
from datetime import datetime

import httpx
import pytest

from app.gateways import get_gateway
from app.gateways.base import (APPROVED, EXPIRED, PENDING, REFUNDED, REJECTED, Address, ChargeRequest, GatewayError,
                               Payer, WebhookRejected)
from app.gateways.mercadopago import MercadoPagoGateway
from tests.conftest import add_to_cart, bearer, checkout, register

NOTIFY = "https://api.exemplo.com/webhooks/mercadopago?source_news=webhooks"
EXPIRES = datetime(2026, 10, 14, 15, 0, 0)  # 12:00 em Brasília

PIX_RESPONSE = {
    "id": 555, "status": "pending", "status_detail": "pending_waiting_transfer", "payment_method_id": "pix",
    "payment_type_id": "bank_transfer", "date_of_expiration": "2026-10-14T12:00:00.000-03:00",
    "transaction_details": {"total_paid_amount": 0, "external_resource_url": None},
    "point_of_interaction": {"transaction_data": {"qr_code": "00020126PIXREAL", "qr_code_base64": "iVBORw0KGgo=",
                                                  "ticket_url": "https://www.mercadopago.com.br/payments/555/ticket"}}}
BOLETO_RESPONSE = {
    "id": 777, "status": "pending", "status_detail": "pending_waiting_payment", "payment_method_id": "bolbradesco",
    "payment_type_id": "ticket", "date_of_expiration": "2026-10-17T23:59:59.000-03:00",
    "barcode": {"content": "23793381286000000000300000000001712340000749000"},
    "transaction_details": {"external_resource_url": "https://www.mercadopago.com.br/payments/777/ticket?hash=abc",
                            "digitable_line": "23793.38128 60000.000003 00000.000017 1 71234000074900"}}
CARD_RESPONSE = {"id": 888, "status": "approved", "status_detail": "accredited", "payment_method_id": "visa",
                 "payment_type_id": "credit_card", "transaction_details": {"total_paid_amount": 67.41}}


def payer(address=True):
    addr = Address("01310100", "Avenida Paulista", "1000", "Bela Vista", "São Paulo", "SP") if address else None
    return Payer("Ana Souza Lima", "ana@exemplo.com", "52998224725", "+5511987654321", addr)


def request_for(method, **over):
    base = dict(payment_id="pay-uuid-1", order_code="CM-ABC234", amount_cents=7490, total_with_interest_cents=7490,
                description="Criando Memórias CM-ABC234: Festa Abelhinha", method=method, installments=1, payer=payer(),
                expires_at=EXPIRES)
    base.update(over)
    return ChargeRequest(**base)


def gateway(handler, secret="segredo-do-webhook"):
    client = httpx.Client(base_url="https://api.mercadopago.com", transport=httpx.MockTransport(handler))
    return MercadoPagoGateway("TEST-token", secret, NOTIFY, client=client)


class Recorder:
    def __init__(self, response, status=200):
        self.response, self.status, self.requests = response, status, []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return httpx.Response(self.status, json=self.response)

    @property
    def body(self):
        return json.loads(self.requests[-1].content)


# ---------- criar cobrança ----------
def test_pix_request_and_response():
    rec = Recorder(PIX_RESPONSE)
    res = gateway(rec).create_charge(request_for("pix"))
    req = rec.requests[0]
    assert req.method == "POST" and req.url.path == "/v1/payments"
    assert req.headers["authorization"] == "Bearer TEST-token" and req.headers["x-idempotency-key"] == "pay-uuid-1"
    b = rec.body
    assert b["transaction_amount"] == 74.9 and b["payment_method_id"] == "pix" and b["external_reference"] == "CM-ABC234"
    assert b["notification_url"] == NOTIFY and b["date_of_expiration"] == "2026-10-14T12:00:00.000-03:00"
    assert b["payer"] == {"email": "ana@exemplo.com", "first_name": "Ana", "last_name": "Souza Lima",
                          "identification": {"type": "CPF", "number": "52998224725"}}
    assert (res.provider_payment_id, res.status) == ("555", PENDING)
    assert res.pix_qr_code == "00020126PIXREAL" and res.pix_qr_code_base64 == "iVBORw0KGgo="
    assert res.pix_ticket_url.endswith("/555/ticket") and res.expires_at == EXPIRES


def test_boleto_request_and_response():
    rec = Recorder(BOLETO_RESPONSE)
    res = gateway(rec).create_charge(request_for("boleto"))
    b = rec.body
    assert b["payment_method_id"] == "bolbradesco"
    assert b["payer"]["address"] == {"zip_code": "01310100", "street_name": "Avenida Paulista", "street_number": "1000",
                                     "neighborhood": "Bela Vista", "city": "São Paulo", "federal_unit": "SP"}
    assert res.status == PENDING and res.boleto_url.startswith("https://www.mercadopago.com.br/payments/777")
    assert res.boleto_barcode.startswith("2379338128") and res.boleto_digitable_line.startswith("23793.38128")
    assert res.pix_qr_code is None


def test_boleto_requires_address():
    with pytest.raises(GatewayError):
        gateway(Recorder(BOLETO_RESPONSE)).create_charge(request_for("boleto", payer=payer(address=False)))


def test_card_request_and_response():
    rec = Recorder(CARD_RESPONSE)
    res = gateway(rec).create_charge(request_for("card", installments=3, card_token="tok-do-sdk", card_brand="visa",
                                                 amount_cents=6741, total_with_interest_cents=6741, expires_at=None))
    b = rec.body
    assert b["token"] == "tok-do-sdk" and b["installments"] == 3 and b["payment_method_id"] == "visa"
    assert "date_of_expiration" not in b and b["transaction_amount"] == 67.41
    assert res.status == APPROVED and res.total_paid_cents == 6741


def test_card_without_token_is_rejected_before_calling_api():
    rec = Recorder(CARD_RESPONSE)
    with pytest.raises(GatewayError):
        gateway(rec).create_charge(request_for("card", card_token=None, card_brand=None))
    assert rec.requests == []


# ---------- consultar, cancelar, estados ----------
def test_get_payment_and_status_mapping():
    cases = [({"status": "approved"}, APPROVED), ({"status": "in_process"}, PENDING), ({"status": "pending"}, PENDING),
             ({"status": "authorized"}, PENDING), ({"status": "rejected"}, REJECTED),
             ({"status": "cancelled", "status_detail": "expired"}, EXPIRED), ({"status": "refunded"}, REFUNDED),
             ({"status": "charged_back"}, REFUNDED), ({"status": "algo_novo"}, PENDING)]
    for extra, expected in cases:
        rec = Recorder({"id": 1, **extra})
        assert gateway(rec).get_payment("1").status == expected, extra
        assert rec.requests[0].method == "GET" and rec.requests[0].url.path == "/v1/payments/1"
    assert gateway(Recorder({"id": 1, "status": "cancelled"})).get_payment("1").status == "cancelled"


def test_cancel_payment():
    rec = Recorder({"id": 1, "status": "cancelled"})
    gateway(rec).cancel_payment("1")
    assert rec.requests[0].method == "PUT" and rec.body == {"status": "cancelled"}


# ---------- erros ----------
def test_api_errors_become_gateway_errors():
    with pytest.raises(GatewayError) as bad:
        gateway(Recorder({"error": "bad_request", "cause": [{"code": 2067}]}, 400)).create_charge(request_for("pix"))
    assert bad.value.retryable is False and "CPF" in bad.value.message
    with pytest.raises(GatewayError) as down:
        gateway(Recorder({"message": "boom"}, 503)).create_charge(request_for("pix"))
    assert down.value.retryable is True

    def unreachable(request):
        raise httpx.ConnectError("sem rede")

    with pytest.raises(GatewayError) as net:
        gateway(unreachable).create_charge(request_for("pix"))
    assert net.value.retryable is True


# ---------- webhook ----------
def signed(secret, data_id, request_id="req-1", ts="1700000000"):
    manifest = f"id:{data_id.lower()};request-id:{request_id};ts:{ts};"
    v1 = hmac.new(secret.encode(), manifest.encode(), hashlib.sha256).hexdigest()
    return {"x-signature": f"ts={ts},v1={v1}", "x-request-id": request_id}


def test_webhook_signature_ok_and_failures():
    gw = gateway(Recorder({}))
    q = {"data.id": "ABC123", "type": "payment"}
    assert gw.verify_webhook(signed("segredo-do-webhook", "ABC123"), q, b"{}") == "ABC123"
    with pytest.raises(WebhookRejected):
        gw.verify_webhook(signed("outro-segredo", "ABC123"), q, b"{}")
    with pytest.raises(WebhookRejected):
        gw.verify_webhook({}, q, b"{}")
    with pytest.raises(WebhookRejected):
        gw.verify_webhook({"x-signature": "lixo"}, q, b"{}")
    with pytest.raises(WebhookRejected):  # assinatura de um pagamento usada em outro
        gw.verify_webhook(signed("segredo-do-webhook", "AAA"), {"data.id": "BBB", "type": "payment"}, b"{}")
    with pytest.raises(WebhookRejected):
        gw.verify_webhook(signed("segredo-do-webhook", "1"), {"type": "payment"}, b"{}")  # sem id


def test_webhook_id_from_body_and_other_topics_ignored():
    gw = gateway(Recorder({}))
    body = json.dumps({"type": "payment", "data": {"id": "999"}}).encode()
    assert gw.verify_webhook(signed("segredo-do-webhook", "999"), {}, body) == "999"
    assert gw.verify_webhook({}, {"type": "merchant_order", "data.id": "1"}, b"{}") is None


def test_webhook_without_secret_still_accepts_but_state_is_refetched():
    gw = gateway(Recorder({}), secret="")
    assert gw.verify_webhook({}, {"data.id": "5", "type": "payment"}, b"{}") == "5"


# ---------- ponta a ponta pela API, com o Mercado Pago simulado ----------
def test_end_to_end_pix_through_api(client):
    state = {"status": "pending"}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            return httpx.Response(201, json=PIX_RESPONSE)
        if request.method == "GET":
            data = {**PIX_RESPONSE, "status": state["status"]}
            if state["status"] == "approved":
                data["transaction_details"] = {"total_paid_amount": 67.41}
            return httpx.Response(200, json=data)
        return httpx.Response(200, json={"id": 555, "status": "cancelled"})

    gw = gateway(handler)
    client.app.dependency_overrides[get_gateway] = lambda: gw
    try:
        t = register(client)
        add_to_cart(client, 1, bearer(t))
        o = checkout(client, t).json()
        assert o["payment"]["provider"] == "mercadopago" and o["payment"]["pix"]["qr_code"] == "00020126PIXREAL"
        assert o["payment"]["pix"]["qr_code_base64"] == "iVBORw0KGgo="

        # aviso com assinatura errada: ignorado
        bad = client.post("/webhooks/mercadopago?data.id=555&type=payment", json={}, headers={"x-signature": "ts=1,v1=00"})
        assert bad.status_code == 401
        assert client.get(f"/orders/{o['id']}", headers=bearer(t)).json()["status"] == "pending"

        # cliente pagou: a operadora avisa; o backend reconsulta e marca como pago
        state["status"] = "approved"
        ok = client.post("/webhooks/mercadopago?data.id=555&type=payment", json={},
                         headers=signed("segredo-do-webhook", "555"))
        assert ok.status_code == 200 and ok.json()["status"] == "paid"
        got = client.get(f"/orders/{o['id']}", headers=bearer(t)).json()
        assert got["status"] == "paid" and got["payment"]["total_paid_cents"] == 6741
        assert len(client.get("/me/library", headers=bearer(t)).json()) == 1
    finally:
        client.app.dependency_overrides.clear()


def test_polling_picks_up_payment_when_webhook_never_arrives(client):
    """Se o aviso se perder, consultar o pedido (acompanhamento do Pix na tela) reconcilia sozinho."""
    state = {"status": "pending"}

    def handler(request):
        if request.method == "POST":
            return httpx.Response(201, json=PIX_RESPONSE)
        return httpx.Response(200, json={**PIX_RESPONSE, "status": state["status"]})

    gw = gateway(handler)
    client.app.dependency_overrides[get_gateway] = lambda: gw
    try:
        t = register(client)
        add_to_cart(client, 1, bearer(t))
        o = checkout(client, t).json()
        state["status"] = "approved"
        # o intervalo mínimo entre consultas (15 s) evita martelar a operadora; o admin pode forçar
        assert client.get(f"/orders/{o['id']}", headers=bearer(t)).json()["status"] == "pending"
        r = client.post(f"/admin/orders/{o['id']}/reconcile", headers={"X-Admin-Key": "admin-teste"})
        assert r.status_code == 200 and r.json()["status"] == "paid"
        assert r.json()["payer_cpf_masked"] == "***.982.247-**"
    finally:
        client.app.dependency_overrides.clear()


def test_gateway_down_marks_order_failed_and_reports(client):
    def handler(request):
        return httpx.Response(503, json={"message": "fora do ar"})

    gw = gateway(handler)
    client.app.dependency_overrides[get_gateway] = lambda: gw
    try:
        t = register(client)
        add_to_cart(client, 1, bearer(t))
        r = checkout(client, t)
        assert r.status_code == 502 and r.json()["error"]["code"] == "payment_gateway_error"
        assert client.get("/orders", headers=bearer(t)).json()[0]["status"] == "failed"
        assert client.get("/cart", headers=bearer(t)).json()["items_count"] == 1
    finally:
        client.app.dependency_overrides.clear()
