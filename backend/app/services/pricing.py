"""Preço: desconto de primeira compra e opções de parcelamento no cartão.

O valor cobrado de verdade (juros, taxas) é definido pela operadora de pagamento; as parcelas calculadas aqui
servem para a tela mostrar as opções e para o simulador. Mantenha MONTHLY_INTEREST_PERCENT igual ao que a
operadora cobra do cliente."""
import math
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import Settings
from ..models import Order, User
from ..schemas import DiscountInfo, InstallmentOption

FIRST_PURCHASE_CODE = "PRIMEIRA_COMPRA"


def first_purchase_discount_cents(subtotal_cents: int, s: Settings) -> int:
    if s.first_purchase_discount_percent <= 0 or subtotal_cents <= 0:
        return 0
    amount = int(subtotal_cents * s.first_purchase_discount_percent // 100)
    if s.first_purchase_discount_max_cents > 0:
        amount = min(amount, s.first_purchase_discount_max_cents)
    return amount


def has_paid_order(db: Session, user_id: Optional[str] = None, cpf_hash: Optional[str] = None) -> bool:
    """Já houve compra paga (ou paga e depois reembolsada) por este usuário ou por este CPF?"""
    stmt = select(Order.id).where(Order.status.in_(("paid", "refunded"))).limit(1)
    if user_id is not None:
        if db.scalar(stmt.where(Order.user_id == user_id)):
            return True
    if cpf_hash is not None:
        if db.scalar(stmt.where(Order.payer_cpf_hash == cpf_hash)):
            return True
    return False


def discount_info(db: Session, s: Settings, user: Optional[User], subtotal_cents: int) -> DiscountInfo:
    pct = s.first_purchase_discount_percent
    if pct <= 0:
        return DiscountInfo(percent=0, status="disabled", estimated_amount_cents=0)
    estimate = first_purchase_discount_cents(subtotal_cents, s)
    if user is None:
        return DiscountInfo(percent=pct, status="login_required", estimated_amount_cents=estimate)
    if has_paid_order(db, user_id=user.id):
        return DiscountInfo(percent=pct, status="used", estimated_amount_cents=0)
    return DiscountInfo(percent=pct, status="eligible", estimated_amount_cents=estimate)


def installment_options(amount_cents: int, s: Settings) -> List[InstallmentOption]:
    """Opções de 1x até MAX_INSTALLMENTS, respeitando o valor mínimo da parcela."""
    options: List[InstallmentOption] = []
    if amount_cents <= 0:
        return options
    rate = s.monthly_interest_percent / 100
    for n in range(1, s.max_installments + 1):
        if n > 1 and amount_cents / n < s.min_installment_cents:
            break
        if n == 1 or n <= s.interest_free_installments or rate <= 0:
            options.append(InstallmentOption(installments=n, installment_cents=math.ceil(amount_cents / n),
                                             total_cents=amount_cents, interest_free=True))
        else:  # tabela Price: parcela fixa com juros compostos
            per = int(round(amount_cents * rate / (1 - (1 + rate) ** -n)))
            options.append(InstallmentOption(installments=n, installment_cents=per, total_cents=per * n,
                                             interest_free=False))
    return options
