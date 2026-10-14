"""Simulador de pagamento, para você testar as telas sem operadora. Só existe com ENV=dev e PAYMENT_GATEWAY=simulated."""
from typing import Literal

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..config import Settings, get_settings
from ..db import get_db
from ..errors import not_found
from ..gateways import get_gateway
from ..gateways.simulated import SimulatedGateway
from ..models import Order
from ..schemas import OrderOut
from ..services import orders

router = APIRouter(prefix="/dev", tags=["Desenvolvimento (simulador)"])
_STATUS = {"approve": "approved", "reject": "rejected", "expire": "expired"}


@router.post("/orders/{order_id}/{action}", response_model=OrderOut,
             summary="Simular o pagamento: approve (cliente pagou), reject ou expire")
def simulate(order_id: str, action: Literal["approve", "reject", "expire"], db: Session = Depends(get_db),
             s: Settings = Depends(get_settings), gateway=Depends(get_gateway)):
    if s.is_production or not isinstance(gateway, SimulatedGateway):
        raise not_found("Rota não encontrada.")
    order = db.get(Order, order_id)
    payment = orders.current_payment(order) if order is not None else None
    if order is None or payment is None or not payment.provider_payment_id:
        raise not_found("Pedido não encontrado.", "order_not_found")
    gateway.set_status(payment.provider_payment_id, _STATUS[action],
                       order.charged_cents if action == "approve" else None)
    orders.process_notification(db, gateway, payment.provider_payment_id)
    db.refresh(order)
    return orders.order_out(order)
