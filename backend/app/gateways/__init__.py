"""Escolhe o gateway pela variável PAYMENT_GATEWAY. Para incluir outra operadora, registre-a aqui."""
from typing import Dict

from ..config import Settings, get_settings
from .base import PaymentGateway

_instances: Dict[str, PaymentGateway] = {}


def build_gateway(settings: Settings) -> PaymentGateway:
    name = settings.payment_gateway
    if name == "simulated":
        from .simulated import SimulatedGateway
        return SimulatedGateway(settings.simulated_webhook_secret)
    if name == "mercadopago":
        from .mercadopago import MercadoPagoGateway
        notify = f"{settings.public_api_url}/webhooks/mercadopago?source_news=webhooks" if settings.public_api_url else ""
        return MercadoPagoGateway(settings.mercadopago_access_token, settings.mercadopago_webhook_secret, notify)
    raise RuntimeError(f"PAYMENT_GATEWAY desconhecido: {name!r}. Use 'simulated' ou 'mercadopago'.")


def get_gateway() -> PaymentGateway:
    """Dependência do FastAPI. Uma instância por nome de gateway (o simulador guarda estado em memória)."""
    settings = get_settings()
    key = settings.payment_gateway
    if key not in _instances:
        _instances[key] = build_gateway(settings)
    return _instances[key]


def reset_gateways() -> None:
    _instances.clear()
