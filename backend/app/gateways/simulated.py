"""Gateway simulado: permite testar carrinho, Pix, boleto e cartão sem conta em nenhuma operadora.
Nada aqui cobra de verdade. Os códigos gerados são falsos e não funcionam em aplicativo de banco.

Cartão: use `card_token` = "tok_approved" (aprova), "tok_rejected" (recusa) ou "tok_pending" (fica em análise).
Pix e boleto ficam pendentes até você confirmar em POST /dev/payments/{id}/approve (só em ENV=dev)."""
import hashlib
import hmac
import json
import uuid
from typing import Dict, Mapping, Optional

from .base import (APPROVED, PENDING, REJECTED, ChargeRequest, ChargeResult, GatewayError, PaymentGateway,
                   WebhookRejected)

# estado "da operadora" simulada; vive na memória do processo
_STATE: Dict[str, ChargeResult] = {}


class SimulatedGateway(PaymentGateway):
    name = "simulated"

    def __init__(self, webhook_secret: str):
        self.webhook_secret = webhook_secret

    def create_charge(self, req: ChargeRequest) -> ChargeResult:
        pid = "sim_" + uuid.uuid4().hex[:16]
        if req.method == "pix":
            res = ChargeResult(
                pid, PENDING, "pending_waiting_transfer",
                pix_qr_code=f"00020126SIMULADO{pid}520400005303986540{req.amount_cents / 100:.2f}5802BR5925CRIANDO MEMORIAS SIMULADO6009SAO PAULO6304FAKE",
                pix_ticket_url=f"https://simulado.invalid/pix/{pid}", expires_at=req.expires_at)
        elif req.method == "boleto":
            digits = hashlib.sha256(pid.encode()).hexdigest()
            numeric = "".join(str(int(c, 16) % 10) for c in digits)[:47]
            res = ChargeResult(
                pid, PENDING, "pending_waiting_payment",
                boleto_barcode=numeric[:44], boleto_digitable_line=numeric,
                boleto_url=f"https://simulado.invalid/boleto/{pid}", expires_at=req.expires_at)
        elif req.method == "card":
            if not req.card_token or not req.card_token.startswith("tok_"):
                raise GatewayError("Cartão inválido. Confira os dados e tente de novo.")
            if req.card_token == "tok_approved":
                res = ChargeResult(pid, APPROVED, "accredited", total_paid_cents=req.total_with_interest_cents)
            elif req.card_token == "tok_pending":
                res = ChargeResult(pid, PENDING, "pending_review_manual")
            else:
                res = ChargeResult(pid, REJECTED, "cc_rejected_insufficient_amount")
        else:
            raise GatewayError("Forma de pagamento não suportada.")
        _STATE[pid] = res
        return res

    def get_payment(self, provider_payment_id: str) -> ChargeResult:
        res = _STATE.get(provider_payment_id)
        if res is None:  # processo reiniciado: o banco do site é a referência
            return ChargeResult(provider_payment_id, PENDING, "unknown_after_restart")
        return res

    def cancel_payment(self, provider_payment_id: str) -> None:
        res = _STATE.get(provider_payment_id)
        if res is not None and res.status == PENDING:
            res.status = "cancelled"

    # --- uso interno do simulador ---
    def set_status(self, provider_payment_id: str, status: str, total_paid_cents: Optional[int] = None) -> ChargeResult:
        res = _STATE.get(provider_payment_id)
        if res is None:
            res = ChargeResult(provider_payment_id, PENDING)
            _STATE[provider_payment_id] = res
        res.status = status
        res.status_detail = {"approved": "accredited", "rejected": "cc_rejected_other_reason",
                             "expired": "expired"}.get(status, status)
        if total_paid_cents is not None:
            res.total_paid_cents = total_paid_cents
        return res

    def sign(self, body: bytes) -> str:
        return hmac.new(self.webhook_secret.encode(), body, hashlib.sha256).hexdigest()

    def verify_webhook(self, headers: Mapping[str, str], query: Mapping[str, str], body: bytes) -> Optional[str]:
        given = headers.get("x-signature", "")
        if not hmac.compare_digest(given, self.sign(body)):
            raise WebhookRejected("assinatura inválida")
        try:
            data = json.loads(body.decode("utf-8"))
            pid = str(data["payment_id"])
        except Exception:
            raise WebhookRejected("corpo inválido")
        status = data.get("status")
        if status:  # no simulador o aviso carrega o novo estado
            self.set_status(pid, status, data.get("total_paid_cents"))
        return pid
