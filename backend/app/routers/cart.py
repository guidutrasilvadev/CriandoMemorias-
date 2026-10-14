"""Carrinho. Visitante: guarde o `cart_id` devolvido e envie no cabeçalho X-Cart-Id. Logado: não precisa."""
from typing import Optional

from fastapi import APIRouter, Depends, Header, Response
from sqlalchemy.orm import Session

from ..config import Settings, get_settings
from ..db import get_db
from ..deps import current_user_optional
from ..models import User
from ..schemas import CartAddIn, CartOut
from ..services import cart as cart_service

router = APIRouter(prefix="/cart", tags=["Carrinho"])
CartHeader = Header(None, alias="X-Cart-Id", description="Id do carrinho de visitante (devolvido em `cart_id`)")


def _respond(response: Response, db: Session, s: Settings, user: Optional[User], cart) -> CartOut:
    if cart is not None and user is None:
        response.headers["X-Cart-Id"] = cart.id
    return cart_service.serialize(db, s, user, cart)


@router.get("", response_model=CartOut, summary="Ver o carrinho (com desconto e parcelas)")
def get_cart(response: Response, x_cart_id: Optional[str] = CartHeader, db: Session = Depends(get_db),
             s: Settings = Depends(get_settings), user: Optional[User] = Depends(current_user_optional)):
    cart = cart_service.resolve_cart(db, user, x_cart_id, create=False)
    return _respond(response, db, s, user, cart)


@router.post("/items", response_model=CartOut, summary="Adicionar um kit")
def add_item(body: CartAddIn, response: Response, x_cart_id: Optional[str] = CartHeader, db: Session = Depends(get_db),
             s: Settings = Depends(get_settings), user: Optional[User] = Depends(current_user_optional)):
    cart = cart_service.resolve_cart(db, user, x_cart_id, create=True)
    cart_service.add_item(db, cart, body.product_id)
    return _respond(response, db, s, user, cart)


@router.delete("/items/{product_id}", response_model=CartOut, summary="Remover um kit")
def remove_item(product_id: int, response: Response, x_cart_id: Optional[str] = CartHeader,
                db: Session = Depends(get_db), s: Settings = Depends(get_settings),
                user: Optional[User] = Depends(current_user_optional)):
    cart = cart_service.resolve_cart(db, user, x_cart_id, create=False)
    if cart is not None:
        cart_service.remove_item(db, cart, product_id)
    return _respond(response, db, s, user, cart)


@router.delete("", response_model=CartOut, summary="Esvaziar o carrinho")
def clear_cart(response: Response, x_cart_id: Optional[str] = CartHeader, db: Session = Depends(get_db),
               s: Settings = Depends(get_settings), user: Optional[User] = Depends(current_user_optional)):
    cart = cart_service.resolve_cart(db, user, x_cart_id, create=False)
    if cart is not None:
        cart_service.clear(db, cart)
    return _respond(response, db, s, user, cart)
