"""Saúde do servidor e configurações públicas que as telas precisam conhecer."""
from fastapi import APIRouter, Depends

from ..config import Settings, get_settings

router = APIRouter(tags=["Geral"])


@router.get("/health", summary="O servidor está no ar?")
def health():
    return {"status": "ok"}


@router.get("/config/public", summary="Configurações públicas (parcelas, prazos, desconto, chaves públicas de login e cartão)")
def public_config(s: Settings = Depends(get_settings)):
    return {
        "currency": "BRL",
        "payment_methods": ["pix", "boleto", "card"],
        "min_order_cents": s.min_order_cents,
        "installments": {"max": s.max_installments, "interest_free": s.interest_free_installments,
                         "min_installment_cents": s.min_installment_cents,
                         "monthly_interest_percent": s.monthly_interest_percent},
        "pix_expiration_minutes": s.pix_expiration_minutes,
        "boleto_due_days": s.boleto_due_days,
        "first_purchase_discount_percent": s.first_purchase_discount_percent,
        "login": {"google_client_id": s.google_client_id or None, "facebook_app_id": s.facebook_app_id or None},
        # a tela de cartão usa o SDK da operadora com esta chave pública para gerar o card_token
        "card": {"provider": s.payment_gateway, "public_key": s.mercadopago_public_key or None},
    }
