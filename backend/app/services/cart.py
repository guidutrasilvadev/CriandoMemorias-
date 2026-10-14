"""Carrinho. Visitante: identificado pelo cabeçalho X-Cart-Id (um UUID impossível de adivinhar).
Usuário logado: um carrinho por conta; o carrinho de visitante é mesclado ao entrar."""
from typing import Optional

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..config import Settings
from ..errors import not_found
from ..models import Cart, CartItem, Product, User
from ..schemas import CartItemOut, CartOut
from . import pricing
from .catalog import product_out


def _guest_cart(db: Session, cart_id: Optional[str]) -> Optional[Cart]:
    if not cart_id:
        return None
    cart = db.get(Cart, cart_id)
    return cart if cart is not None and cart.user_id is None else None


def resolve_cart(db: Session, user: Optional[User], cart_id: Optional[str], create: bool) -> Optional[Cart]:
    """Devolve o carrinho de quem está chamando (e mescla o de visitante, se veio junto com o login)."""
    guest = _guest_cart(db, cart_id)
    if user is None:
        if guest is None and create:
            guest = Cart()
            db.add(guest)
            db.commit()
        return guest
    cart = db.scalar(select(Cart).where(Cart.user_id == user.id))
    if cart is None:
        cart = Cart(user_id=user.id)
        db.add(cart)
        try:
            db.flush()
        except IntegrityError:  # duas chamadas ao mesmo tempo criaram o carrinho: usa o que ficou
            db.rollback()
            cart = db.scalar(select(Cart).where(Cart.user_id == user.id))
    if guest is not None:
        have = {i.product_id for i in cart.items}
        for item in list(guest.items):
            if item.product_id not in have:
                db.add(CartItem(cart_id=cart.id, product_id=item.product_id, added_at=item.added_at))
        db.delete(guest)
    db.commit()
    db.refresh(cart)
    return cart


def add_item(db: Session, cart: Cart, product_id: int) -> None:
    product = db.get(Product, product_id)
    if product is None or not product.active:
        raise not_found("Este kit não está disponível.", "product_not_found")
    if any(i.product_id == product_id for i in cart.items):
        return  # kit digital: não há quantidade, adicionar de novo não muda nada
    db.add(CartItem(cart_id=cart.id, product_id=product_id))
    db.commit()
    db.refresh(cart)


def remove_item(db: Session, cart: Cart, product_id: int) -> None:
    db.execute(delete(CartItem).where(CartItem.cart_id == cart.id, CartItem.product_id == product_id))
    db.commit()
    db.refresh(cart)


def clear(db: Session, cart: Cart) -> None:
    db.execute(delete(CartItem).where(CartItem.cart_id == cart.id))
    db.commit()
    db.refresh(cart)


def serialize(db: Session, settings: Settings, user: Optional[User], cart: Optional[Cart]) -> CartOut:
    items = []
    unavailable = []
    if cart is not None:
        for i in cart.items:
            (items if i.product.active else unavailable).append(i)
    subtotal = sum(i.product.price_cents for i in items)
    info = pricing.discount_info(db, settings, user, subtotal)
    discount = info.estimated_amount_cents if info.status == "eligible" else 0
    total = subtotal - discount
    return CartOut(
        cart_id=cart.id if cart is not None else None,
        items=[CartItemOut(product=product_out(i.product), added_at=i.added_at) for i in items],
        items_count=len(items), subtotal_cents=subtotal, discount_cents=discount, total_cents=total,
        first_purchase_discount=info, installment_options=pricing.installment_options(total, settings),
        unavailable_product_ids=[i.product_id for i in unavailable])


def active_items(cart: Cart):
    return [i for i in cart.items if i.product.active]
