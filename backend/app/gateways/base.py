"""Contrato dos gateways de pagamento. Para usar outra operadora (Asaas, Pagar.me, Stripe...),
crie uma classe que implemente `PaymentGateway` e registre em `app/gateways/__init__.py`."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Mapping, Optional

# status normalizados de pagamento (iguais para qualquer operadora)
PENDING, APPROVED, REJECTED, CANCELLED, EXPIRED, REFUNDED = "pending", "approved", "rejected", "cancelled", "expired", "refunded"


class GatewayError(Exception):
    """Falha ao falar com a operadora (rede, credencial, dados recusados). `message` pode ir para o cliente."""

    def __init__(self, message: str, retryable: bool = False):
        super().__init__(message)
        self.message = message
        self.retryable = retryable


class WebhookRejected(Exception):
    """Aviso (webhook) com assinatura inválida ou formato inesperado."""


@dataclass
class Address:
    zip_code: str
    street: str
    number: str
    neighborhood: str
    city: str
    state: str
    complement: str = ""


@dataclass
class Payer:
    name: str
    email: str
    cpf: str  # só dígitos
    phone: Optional[str] = None
    address: Optional[Address] = None


@dataclass
class ChargeRequest:
    payment_id: str  # id interno do pagamento; serve de chave de idempotência na operadora
    order_code: str
    amount_cents: int  # valor-base do pedido (já com desconto), sem juros
    total_with_interest_cents: int  # o que o cliente deve pagar no total (igual ao base quando sem juros)
    description: str
    method: str  # pix | boleto | card
    installments: int
    payer: Payer
    expires_at: Optional[datetime] = None  # UTC (naive). Pix e boleto.
    card_token: Optional[str] = None  # token gerado no navegador pelo SDK da operadora (o backend nunca vê o cartão)
    card_brand: Optional[str] = None  # ex.: visa, master, elo (payment_method_id da operadora)


@dataclass
class ChargeResult:
    provider_payment_id: str
    status: str
    status_detail: str = ""
    pix_qr_code: Optional[str] = None  # texto "copia e cola"
    pix_qr_code_base64: Optional[str] = None  # imagem PNG em base64 (se a operadora fornecer)
    pix_ticket_url: Optional[str] = None
    boleto_barcode: Optional[str] = None
    boleto_digitable_line: Optional[str] = None
    boleto_url: Optional[str] = None
    expires_at: Optional[datetime] = None
    total_paid_cents: Optional[int] = None
    raw: Dict[str, Any] = field(default_factory=dict)


class PaymentGateway(ABC):
    name: str = ""

    @abstractmethod
    def create_charge(self, req: ChargeRequest) -> ChargeResult: ...

    @abstractmethod
    def get_payment(self, provider_payment_id: str) -> ChargeResult:
        """Consulta o estado atual na operadora. É a fonte da verdade: nunca confie só no corpo do webhook."""

    @abstractmethod
    def cancel_payment(self, provider_payment_id: str) -> None: ...

    @abstractmethod
    def verify_webhook(self, headers: Mapping[str, str], query: Mapping[str, str], body: bytes) -> Optional[str]:
        """Valida o aviso e devolve o id do pagamento na operadora (ou None se o aviso não for de pagamento).
        Lança `WebhookRejected` se a assinatura não bater."""
