"""Pedidos e pagamentos: checkout, mudanças de estado, conciliação com a operadora, cancelamento e biblioteca.

Regras que valem aqui:
- o preço vem sempre do banco, nunca do navegador;
- o pedido e o pagamento são gravados ANTES de chamar a operadora (se algo cair no meio, há registro);
- o estado real do pagamento é sempre reconsultado na operadora (o corpo do webhook não é confiável);
- estados só avançam: pendente -> aprovado/recusado/cancelado/expirado; aprovado -> reembolsado."""
import logging
from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import security, timeutil
from ..config import Settings
from ..errors import ApiError, bad_request, conflict, not_found
from ..fmt import brl
from ..gateways.base import (APPROVED, CANCELLED, EXPIRED, REFUNDED, REJECTED, Address, ChargeRequest, ChargeResult,
                             GatewayError, Payer, PaymentGateway)
from ..models import Cart, CartItem, Order, OrderItem, Payment, User, WebhookEvent
from ..schemas import (BoletoOut, CheckoutIn, LibraryItemOut, OrderItemOut, OrderOut, PaymentOut, PixOut)
from ..validators import mask_cpf
from . import cart as cart_service
from . import pricing
from .catalog import product_out

log = logging.getLogger("cm.orders")

BOLETO_GRACE = timedelta(days=3)  # o boleto pago no vencimento pode levar dias úteis para compensar
OTHER_GRACE = timedelta(minutes=5)
BR_OFFSET = timedelta(hours=3)


# ---------- estados ----------
def current_payment(order: Order) -> Optional[Payment]:
    return order.payments[-1] if order.payments else None


def _clear_cart_items(db: Session, order: Order) -> None:
    cart = db.scalar(select(Cart).where(Cart.user_id == order.user_id))
    if cart is not None:
        db.execute(delete(CartItem).where(CartItem.cart_id == cart.id,
                                          CartItem.product_id.in_([i.product_id for i in order.items])))


def apply_status(db: Session, order: Order, payment: Payment, new_status: str,
                 total_paid_cents: Optional[int] = None) -> bool:
    """Aplica o novo estado do pagamento ao pedido. Só avança; chamar de novo com o mesmo estado não faz nada."""
    old = payment.status
    if new_status in (old, "pending") or old == "refunded":
        return False
    if old == "approved" and new_status != "refunded":
        return False
    payment.status = new_status
    if total_paid_cents is not None:
        payment.total_paid_cents = total_paid_cents
    if new_status == APPROVED:
        # vale também se o pedido já tinha expirado/cancelado: o dinheiro entrou, então o cliente recebe o kit
        order.status = "paid"
        order.paid_at = timeutil.utcnow()
        order.charged_cents = payment.total_paid_cents or order.charged_cents or order.total_cents
        _clear_cart_items(db, order)
        log.info("pedido %s pago (%s)", order.code, payment.method)
    elif new_status == REFUNDED:
        order.status = "refunded"
    elif order.status == "pending":
        order.status = {REJECTED: "failed", "failed": "failed", EXPIRED: "expired", CANCELLED: "canceled"}.get(
            new_status, order.status)
    return True


def apply_result(db: Session, order: Order, payment: Payment, result: ChargeResult) -> None:
    payment.provider_payment_id = result.provider_payment_id
    payment.status_detail = (result.status_detail or "")[:120]
    payment.pix_qr_code = result.pix_qr_code or payment.pix_qr_code
    payment.pix_qr_code_base64 = result.pix_qr_code_base64 or payment.pix_qr_code_base64
    payment.pix_ticket_url = result.pix_ticket_url or payment.pix_ticket_url
    payment.boleto_barcode = result.boleto_barcode or payment.boleto_barcode
    payment.boleto_digitable_line = result.boleto_digitable_line or payment.boleto_digitable_line
    payment.boleto_url = result.boleto_url or payment.boleto_url
    if result.expires_at:
        payment.expires_at = result.expires_at
    payment.last_checked_at = timeutil.utcnow()
    apply_status(db, order, payment, result.status, result.total_paid_cents)


# ---------- checkout ----------
def _order_deadline(method: str, s: Settings, now: datetime) -> datetime:
    if method == "pix":
        return now + timedelta(minutes=s.pix_expiration_minutes)
    if method == "boleto":
        return now + timedelta(days=s.boleto_due_days)
    return now + timedelta(minutes=s.card_order_expiration_minutes)


def _cancel_at_gateway(gateway: PaymentGateway, payment: Payment) -> None:
    if payment.provider_payment_id and payment.status == "pending" and payment.provider == gateway.name:
        try:
            gateway.cancel_payment(payment.provider_payment_id)
        except GatewayError as exc:
            log.warning("não foi possível cancelar %s na operadora: %s", payment.provider_payment_id, exc.message)


def _cancel_other_pending(db: Session, gateway: PaymentGateway, user_id: str) -> None:
    for old in db.scalars(select(Order).where(Order.user_id == user_id, Order.status == "pending")):
        pay = current_payment(old)
        if pay is not None:
            _cancel_at_gateway(gateway, pay)
            apply_status(db, old, pay, CANCELLED)
        else:
            old.status = "canceled"


def create_checkout(db: Session, s: Settings, gateway: PaymentGateway, user: User, cart: Optional[Cart],
                    body: CheckoutIn, idempotency_key: Optional[str]) -> Order:
    if idempotency_key:
        existing = db.scalar(select(Order).where(Order.user_id == user.id, Order.idempotency_key == idempotency_key))
        if existing is not None:
            return existing

    items = cart_service.active_items(cart) if cart is not None else []
    if not items:
        raise bad_request("Seu carrinho está vazio.", "cart_empty")
    if cart is not None and len(items) != len(cart.items):
        raise conflict("Algum kit do carrinho não está mais disponível. Revise o carrinho.", "cart_unavailable_items")
    if any(i.product.demo for i in items) and not s.allow_demo_checkout:
        raise ApiError(403, "demo_catalog", "Este catálogo ainda é de demonstração e não pode ser comprado.")

    subtotal = sum(i.product.price_cents for i in items)
    cpf_hash = security.hmac_hex(s.secret_key, f"cpf:{body.payer.cpf}")
    discount, discount_code = 0, None
    if not pricing.has_paid_order(db, user_id=user.id, cpf_hash=cpf_hash):
        discount = pricing.first_purchase_discount_cents(subtotal, s)
        discount_code = pricing.FIRST_PURCHASE_CODE if discount > 0 else None
    total = subtotal - discount
    if total < s.min_order_cents:
        raise bad_request(f"O valor mínimo do pedido é {brl(s.min_order_cents)}.", "order_too_small")

    installments, charged = 1, total
    if body.payment_method == "card":
        option = next((o for o in pricing.installment_options(total, s) if o.installments == body.installments), None)
        if option is None:
            raise bad_request("Esse parcelamento não está disponível para o valor do pedido.", "invalid_installments")
        installments, charged = option.installments, option.total_cents

    if body.expected_total_cents is not None and body.expected_total_cents != charged:
        # quem paga só é cobrado pelo valor que viu: se o preço mudou, nada é criado nem cobrado
        raise ApiError(409, "price_changed", f"O valor do pedido mudou para {brl(charged)}. Confira o resumo e confirme de novo.",
                       details={"total_cents": total, "charged_cents": charged, "discount_cents": discount, "discount_code": discount_code})

    _cancel_other_pending(db, gateway, user.id)

    now = timeutil.utcnow()
    deadline = _order_deadline(body.payment_method, s, now)
    order = Order(user_id=user.id, status="pending", subtotal_cents=subtotal, discount_cents=discount,
                  discount_code=discount_code, total_cents=total, charged_cents=charged,
                  payment_method=body.payment_method, installments=installments, payer_name=body.payer.name,
                  payer_email=body.payer.email, payer_phone=body.payer.phone, payer_cpf_hash=cpf_hash,
                  payer_cpf_masked=mask_cpf(body.payer.cpf), idempotency_key=idempotency_key, expires_at=deadline)
    for i in items:
        order.items.append(OrderItem(product_id=i.product_id, name=i.product.name, unit_price_cents=i.product.price_cents))
    payment = Payment(provider=gateway.name, method=body.payment_method, status="pending", amount_cents=total,
                      installments=installments, expires_at=deadline)
    order.payments.append(payment)
    db.add(order)
    try:
        db.commit()  # registro garantido antes de falar com a operadora
    except IntegrityError:
        db.rollback()
        if idempotency_key:
            again = db.scalar(select(Order).where(Order.user_id == user.id, Order.idempotency_key == idempotency_key))
            if again is not None:
                return again
        raise conflict("Não foi possível criar o pedido. Tente novamente.", "order_conflict")

    address = None
    if body.payer.address is not None:
        a = body.payer.address
        address = Address(zip_code=a.zip_code, street=a.street, number=a.number, neighborhood=a.neighborhood,
                          city=a.city, state=a.state, complement=a.complement)
    names = ", ".join(i.name for i in order.items)
    request = ChargeRequest(
        payment_id=payment.id, order_code=order.code, amount_cents=total, total_with_interest_cents=charged,
        description=f"Criando Memórias {order.code}: {names}"[:200], method=body.payment_method,
        installments=installments, payer=Payer(name=body.payer.name, email=body.payer.email, cpf=body.payer.cpf,
                                               phone=body.payer.phone, address=address),
        expires_at=deadline if body.payment_method in ("pix", "boleto") else None,
        card_token=body.card_token, card_brand=body.card_brand)
    try:
        result = gateway.create_charge(request)
    except GatewayError as exc:
        payment.status, payment.status_detail = "failed", "gateway_error"
        order.status = "failed"
        db.commit()
        raise ApiError(502 if exc.retryable else 400, "payment_gateway_error", exc.message)
    apply_result(db, order, payment, result)
    db.commit()
    db.refresh(order)
    return order


# ---------- consulta, conciliação, expiração e cancelamento ----------
def get_user_order(db: Session, user: User, order_id: str) -> Order:
    order = db.get(Order, order_id)
    if order is None or order.user_id != user.id:
        raise not_found("Pedido não encontrado.", "order_not_found")
    return order


def refresh_order(db: Session, s: Settings, gateway: PaymentGateway, order: Order, min_interval: int = 15) -> Order:
    """Pergunta à operadora o estado atual (no máximo a cada `min_interval` s) e expira o que passou do prazo."""
    if order.status != "pending":
        return order
    payment = current_payment(order)
    now = timeutil.utcnow()
    if (payment is not None and payment.provider == gateway.name and payment.provider_payment_id
            and payment.status == "pending"
            and (payment.last_checked_at is None or (now - payment.last_checked_at).total_seconds() >= min_interval)):
        try:
            apply_result(db, order, payment, gateway.get_payment(payment.provider_payment_id))
        except GatewayError as exc:
            log.warning("conciliação do pedido %s falhou: %s", order.code, exc.message)
            payment.last_checked_at = now
    if order.status == "pending" and order.expires_at is not None:
        grace = BOLETO_GRACE if order.payment_method == "boleto" else OTHER_GRACE
        if now > order.expires_at + grace and payment is not None:
            _cancel_at_gateway(gateway, payment)
            apply_status(db, order, payment, EXPIRED)
    db.commit()
    return order


def cancel_order(db: Session, gateway: PaymentGateway, order: Order) -> Order:
    if order.status != "pending":
        raise conflict("Só é possível cancelar pedidos que ainda aguardam pagamento.", "order_not_cancelable")
    payment = current_payment(order)
    if payment is not None:
        _cancel_at_gateway(gateway, payment)
        apply_status(db, order, payment, CANCELLED)
    else:
        order.status = "canceled"
    db.commit()
    return order


def list_orders(db: Session, user: User, limit: int = 50) -> List[Order]:
    return list(db.scalars(select(Order).where(Order.user_id == user.id).order_by(Order.created_at.desc()).limit(limit)))


def process_notification(db: Session, gateway: PaymentGateway, provider_payment_id: str) -> Optional[Order]:
    """Chamado pelo webhook: reconsulta o pagamento na operadora e atualiza o pedido. None = pagamento desconhecido."""
    payment = db.scalar(select(Payment).where(Payment.provider == gateway.name,
                                              Payment.provider_payment_id == provider_payment_id).with_for_update())
    if payment is None:
        return None  # with_for_update: no PostgreSQL, dois avisos simultâneos do mesmo pagamento esperam um pelo outro
    result = gateway.get_payment(provider_payment_id)
    order = payment.order
    apply_result(db, order, payment, result)
    try:
        db.add(WebhookEvent(provider=gateway.name, event_key=f"{provider_payment_id}:{result.status}",
                            processed_at=timeutil.utcnow()))
        db.flush()
    except IntegrityError:  # aviso repetido: já foi registrado
        db.rollback()
        payment = db.scalar(select(Payment).where(Payment.provider == gateway.name,
                                                  Payment.provider_payment_id == provider_payment_id))
        return payment.order if payment else None
    db.commit()
    return order


# ---------- saída ----------
def payment_out(p: Payment) -> PaymentOut:
    pix = boleto = None
    if p.method == "pix":
        pix = PixOut(qr_code=p.pix_qr_code, qr_code_base64=p.pix_qr_code_base64, ticket_url=p.pix_ticket_url,
                     expires_at=p.expires_at)
    elif p.method == "boleto":
        due = (p.expires_at - BR_OFFSET).date() if p.expires_at else None
        boleto = BoletoOut(barcode=p.boleto_barcode, digitable_line=p.boleto_digitable_line, url=p.boleto_url,
                           due_date=due)
    return PaymentOut(id=p.id, provider=p.provider, method=p.method, status=p.status, status_detail=p.status_detail,
                      amount_cents=p.amount_cents, installments=p.installments, total_paid_cents=p.total_paid_cents,
                      pix=pix, boleto=boleto)


def order_out(o: Order) -> OrderOut:
    pay = current_payment(o)
    return OrderOut(
        id=o.id, code=o.code, status=o.status,
        items=[OrderItemOut(product_id=i.product_id, name=i.name, unit_price_cents=i.unit_price_cents) for i in o.items],
        subtotal_cents=o.subtotal_cents, discount_cents=o.discount_cents, discount_code=o.discount_code,
        total_cents=o.total_cents, charged_cents=o.charged_cents, payment_method=o.payment_method,
        installments=o.installments, payment=payment_out(pay) if pay else None, created_at=o.created_at,
        expires_at=o.expires_at, paid_at=o.paid_at)


def library(db: Session, user: User) -> List[LibraryItemOut]:
    rows = db.execute(select(OrderItem, Order).join(Order, OrderItem.order_id == Order.id)
                      .where(Order.user_id == user.id, Order.status == "paid").order_by(Order.paid_at.desc()))
    return [LibraryItemOut(product=product_out(item.product), order_id=order.id, order_code=order.code,
                           purchased_at=order.paid_at or order.created_at, download_available=bool(item.product.file_key))
            for item, order in rows]
