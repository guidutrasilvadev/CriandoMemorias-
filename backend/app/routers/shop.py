"""Compra: parcelas, checkout, pedidos e avisos (webhooks) das operadoras de pagamento."""
import re
from typing import List, Optional

from fastapi import APIRouter, Depends, Header, Query, Request
from sqlalchemy.orm import Session

from ..config import Settings, get_settings
from ..db import get_db
from ..deps import current_user, rate_limit
from ..errors import ApiError, bad_request
from ..gateways import get_gateway
from ..gateways.base import GatewayError, PaymentGateway, WebhookRejected
from ..models import User
from ..schemas import CheckoutIn, InstallmentOption, OrderOut
from ..services import cart as cart_service
from ..services import orders, pricing

router = APIRouter(tags=["Compra"])
_IDEMPOTENCY_RE = re.compile(r"^[A-Za-z0-9_\-:.]{8,100}$")


@router.get("/payments/installments", response_model=List[InstallmentOption], summary="Opções de parcelamento no cartão")
def installments(amount_cents: int = Query(..., ge=1, description="Valor em centavos"),
                 s: Settings = Depends(get_settings)):
    return pricing.installment_options(amount_cents, s)


@router.post("/checkout", response_model=OrderOut, summary="Fechar o pedido e iniciar o pagamento (Pix, boleto ou cartão)",
             dependencies=[Depends(rate_limit("checkout", 20, 600))])
def checkout(body: CheckoutIn,
             x_cart_id: Optional[str] = Header(None, alias="X-Cart-Id"),
             idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key",
                                                     description="Uma chave nova por tentativa; repetir a mesma devolve o mesmo pedido"),
             db: Session = Depends(get_db), s: Settings = Depends(get_settings),
             gateway: PaymentGateway = Depends(get_gateway), user: User = Depends(current_user)):
    """Exige login. Usa o carrinho da conta. O preço e o desconto de primeira compra são calculados aqui, não no navegador.
    Cartão recusado volta com 200 e `payment.status = "rejected"`; erro da operadora volta como erro (400/502)."""
    if idempotency_key is not None and not _IDEMPOTENCY_RE.match(idempotency_key):
        raise bad_request("Idempotency-Key inválida (8 a 100 caracteres: letras, números e _-:.).", "invalid_idempotency_key")
    cart = cart_service.resolve_cart(db, user, x_cart_id, create=False)
    order = orders.create_checkout(db, s, gateway, user, cart, body, idempotency_key)
    return orders.order_out(order)


@router.get("/orders", response_model=List[OrderOut], summary="Meus pedidos")
def my_orders(db: Session = Depends(get_db), user: User = Depends(current_user)):
    return [orders.order_out(o) for o in orders.list_orders(db, user)]


@router.get("/orders/{order_id}", response_model=OrderOut,
            summary="Ver um pedido (use para acompanhar o Pix: consulte a cada poucos segundos)")
def get_order(order_id: str, db: Session = Depends(get_db), s: Settings = Depends(get_settings),
              gateway: PaymentGateway = Depends(get_gateway), user: User = Depends(current_user)):
    order = orders.get_user_order(db, user, order_id)
    return orders.order_out(orders.refresh_order(db, s, gateway, order))


@router.post("/orders/{order_id}/cancel", response_model=OrderOut, summary="Cancelar um pedido que ainda aguarda pagamento")
def cancel(order_id: str, db: Session = Depends(get_db), gateway: PaymentGateway = Depends(get_gateway),
           user: User = Depends(current_user)):
    order = orders.get_user_order(db, user, order_id)
    return orders.order_out(orders.cancel_order(db, gateway, order))


async def _raw_body(request: Request) -> bytes:
    return await request.body()


@router.post("/webhooks/{provider}", summary="Aviso da operadora de pagamento (não chame do site)", include_in_schema=True)
def webhook(provider: str, request: Request, body: bytes = Depends(_raw_body), db: Session = Depends(get_db),
            gateway: PaymentGateway = Depends(get_gateway)):
    """Recebe o aviso, confere a assinatura e reconsulta o pagamento na operadora. Responde 404 se o pagamento ainda não
    é conhecido (a operadora tenta de novo mais tarde) e 401 se a assinatura não bater."""
    if provider != gateway.name:
        raise ApiError(404, "unknown_provider", "Operadora desconhecida.")
    try:
        payment_id = gateway.verify_webhook(request.headers, dict(request.query_params), body)
    except WebhookRejected:
        raise ApiError(401, "invalid_webhook", "Aviso não autorizado.")
    if payment_id is None:
        return {"received": True, "ignored": True}
    try:
        order = orders.process_notification(db, gateway, payment_id)
    except GatewayError:
        raise ApiError(502, "gateway_unreachable", "Não foi possível consultar a operadora agora.")
    if order is None:
        raise ApiError(404, "payment_unknown", "Pagamento ainda não conhecido.")
    return {"received": True, "order": order.code, "status": order.status}
