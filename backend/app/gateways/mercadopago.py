"""Adaptador do Mercado Pago (API de Pagamentos v1): Pix, boleto e cartão com parcelas.

ATENÇÃO: escrito a partir da documentação pública e coberto por testes com respostas simuladas, mas AINDA NÃO foi
testado contra o sandbox do Mercado Pago (não havia credenciais). Antes de ir ao ar, faça no sandbox, nesta ordem:
um Pix, um boleto, um cartão aprovado e um recusado, e o recebimento do webhook. Se algum campo da resposta mudou,
o ajuste fica concentrado em `_payload`, `_parse` e `verify_webhook` deste arquivo."""
import hashlib
import hmac
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Mapping, Optional

import httpx

from .base import (APPROVED, CANCELLED, EXPIRED, PENDING, REFUNDED, REJECTED, ChargeRequest, ChargeResult,
                   GatewayError, PaymentGateway, WebhookRejected)

log = logging.getLogger("cm.mercadopago")

_STATUS = {"approved": APPROVED, "authorized": PENDING, "pending": PENDING, "in_process": PENDING,
           "in_mediation": PENDING, "rejected": REJECTED, "cancelled": CANCELLED, "refunded": REFUNDED,
           "charged_back": REFUNDED}
_BR_OFFSET = timedelta(hours=3)  # Brasília: UTC-3, sem horário de verão desde 2019


def _mp_date(dt: datetime) -> str:
    return (dt - _BR_OFFSET).strftime("%Y-%m-%dT%H:%M:%S.000-03:00")


def _parse_date(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).astimezone(timezone.utc).replace(tzinfo=None)
    except ValueError:
        return None


def _cents(value: Any) -> Optional[int]:
    return None if value is None else int(round(float(value) * 100))


class MercadoPagoGateway(PaymentGateway):
    name = "mercadopago"
    BASE_URL = "https://api.mercadopago.com"

    def __init__(self, access_token: str, webhook_secret: str, notification_url: str,
                 client: Optional[httpx.Client] = None):
        self.access_token = access_token
        self.webhook_secret = webhook_secret
        self.notification_url = notification_url
        self.client = client or httpx.Client(base_url=self.BASE_URL, timeout=20.0)

    # ---------- HTTP ----------
    def _request(self, method: str, path: str, body: Optional[dict] = None, idempotency: Optional[str] = None) -> dict:
        headers = {"Authorization": f"Bearer {self.access_token}", "Content-Type": "application/json"}
        if idempotency:
            headers["X-Idempotency-Key"] = idempotency
        try:
            resp = self.client.request(method, path, json=body, headers=headers)
        except httpx.HTTPError as exc:
            log.warning("Mercado Pago inacessível: %s", exc.__class__.__name__)
            raise GatewayError("Não foi possível falar com a operadora de pagamento. Tente novamente.", retryable=True)
        if resp.status_code >= 400:
            try:
                err = resp.json()
            except ValueError:
                err = {}
            causes = [c.get("code") for c in (err.get("cause") or []) if isinstance(c, dict)]
            log.warning("Mercado Pago respondeu %s (%s) causas=%s", resp.status_code, err.get("error"), causes)
            if resp.status_code >= 500:
                raise GatewayError("A operadora de pagamento está instável. Tente novamente em instantes.", True)
            raise GatewayError("A operadora recusou os dados do pagamento. Confira CPF, e-mail e dados do cartão.")
        return resp.json()

    # ---------- cobrança ----------
    def _payload(self, req: ChargeRequest) -> Dict[str, Any]:
        first, _, last = req.payer.name.strip().partition(" ")
        payer: Dict[str, Any] = {"email": req.payer.email, "first_name": first, "last_name": last.strip() or first,
                                 "identification": {"type": "CPF", "number": req.payer.cpf}}
        body: Dict[str, Any] = {
            "transaction_amount": round(req.amount_cents / 100, 2),
            "description": req.description[:200],
            "external_reference": req.order_code,
            "payer": payer,
        }
        if self.notification_url:
            body["notification_url"] = self.notification_url
        if req.method == "pix":
            body["payment_method_id"] = "pix"
            if req.expires_at:
                body["date_of_expiration"] = _mp_date(req.expires_at)
        elif req.method == "boleto":
            body["payment_method_id"] = "bolbradesco"
            a = req.payer.address
            if a is None:
                raise GatewayError("Para boleto é preciso informar o endereço.")
            payer["address"] = {"zip_code": a.zip_code, "street_name": a.street, "street_number": a.number,
                                "neighborhood": a.neighborhood, "city": a.city, "federal_unit": a.state}
            if req.expires_at:
                body["date_of_expiration"] = _mp_date(req.expires_at)
        elif req.method == "card":
            if not req.card_token or not req.card_brand:
                raise GatewayError("Dados do cartão incompletos.")
            body.update({"token": req.card_token, "installments": req.installments,
                         "payment_method_id": req.card_brand})
        else:
            raise GatewayError("Forma de pagamento não suportada.")
        return body

    def _parse(self, data: dict) -> ChargeResult:
        raw_status = data.get("status")
        detail = data.get("status_detail") or ""
        status = _STATUS.get(raw_status, PENDING)
        if raw_status == "cancelled" and detail == "expired":
            status = EXPIRED
        td = data.get("transaction_details") or {}
        poi = (data.get("point_of_interaction") or {}).get("transaction_data") or {}
        barcode = (data.get("barcode") or {}).get("content")
        return ChargeResult(
            provider_payment_id=str(data["id"]), status=status, status_detail=detail,
            pix_qr_code=poi.get("qr_code"), pix_qr_code_base64=poi.get("qr_code_base64"),
            pix_ticket_url=poi.get("ticket_url"),
            boleto_barcode=barcode, boleto_digitable_line=td.get("digitable_line"),
            boleto_url=td.get("external_resource_url") if data.get("payment_type_id") == "ticket" else None,
            expires_at=_parse_date(data.get("date_of_expiration")),
            total_paid_cents=_cents(td.get("total_paid_amount")) if status == APPROVED else None,
            raw={"status": raw_status, "status_detail": detail, "payment_method_id": data.get("payment_method_id")})

    def create_charge(self, req: ChargeRequest) -> ChargeResult:
        data = self._request("POST", "/v1/payments", self._payload(req), idempotency=req.payment_id)
        return self._parse(data)

    def get_payment(self, provider_payment_id: str) -> ChargeResult:
        return self._parse(self._request("GET", f"/v1/payments/{provider_payment_id}"))

    def cancel_payment(self, provider_payment_id: str) -> None:
        self._request("PUT", f"/v1/payments/{provider_payment_id}", {"status": "cancelled"})

    # ---------- webhook ----------
    def verify_webhook(self, headers: Mapping[str, str], query: Mapping[str, str], body: bytes) -> Optional[str]:
        h = {k.lower(): v for k, v in headers.items()}
        try:
            payload = json.loads(body.decode("utf-8")) if body else {}
        except ValueError:
            payload = {}
        topic = query.get("type") or query.get("topic") or payload.get("type") or payload.get("topic")
        if topic and topic != "payment":
            return None  # outros tipos de aviso (ex.: merchant_order) não interessam
        data_id = query.get("data.id") or query.get("id") or (payload.get("data") or {}).get("id")
        if data_id is None:
            raise WebhookRejected("aviso sem id de pagamento")
        data_id = str(data_id)
        if self.webhook_secret:
            parts = dict(p.strip().split("=", 1) for p in h.get("x-signature", "").split(",") if "=" in p)
            ts, v1 = parts.get("ts"), parts.get("v1")
            if not ts or not v1:
                raise WebhookRejected("assinatura ausente")
            manifest = f"id:{data_id.lower()};"
            if h.get("x-request-id"):
                manifest += f"request-id:{h['x-request-id']};"
            manifest += f"ts:{ts};"
            expected = hmac.new(self.webhook_secret.encode(), manifest.encode(), hashlib.sha256).hexdigest()
            if not hmac.compare_digest(expected, v1):
                raise WebhookRejected("assinatura inválida")
        else:
            log.warning("MERCADOPAGO_WEBHOOK_SECRET não definido: aviso aceito sem checar assinatura "
                        "(o estado real é sempre reconsultado na API).")
        return data_id
