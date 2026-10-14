"""Tabelas do banco. Valores em dinheiro são sempre inteiros em centavos (BRL)."""
import secrets
import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import (Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from . import timeutil
from .db import Base

_CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"  # sem letras/números que se confundem (0/O, 1/I/L)


def new_id() -> str:
    return str(uuid.uuid4())


def new_order_code() -> str:
    return "CM-" + "".join(secrets.choice(_CODE_ALPHABET) for _ in range(6))


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(120), default="")
    email: Mapped[Optional[str]] = mapped_column(String(254), unique=True, nullable=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    phone: Mapped[Optional[str]] = mapped_column(String(20), unique=True, nullable=True)
    phone_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    password_hash: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: timeutil.utcnow())
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    identities: Mapped[List["Identity"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Identity(Base):
    """Vínculo entre um usuário e uma conta externa (Google ou Facebook)."""
    __tablename__ = "identities"
    __table_args__ = (UniqueConstraint("provider", "provider_user_id", name="uq_identity_provider_user"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    provider: Mapped[str] = mapped_column(String(20))
    provider_user_id: Mapped[str] = mapped_column(String(100))
    email: Mapped[Optional[str]] = mapped_column(String(254), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: timeutil.utcnow())

    user: Mapped[User] = relationship(back_populates="identities")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: timeutil.utcnow())


class OtpCode(Base):
    __tablename__ = "otp_codes"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    destination: Mapped[str] = mapped_column(String(254), index=True)  # e-mail normalizado ou telefone E.164
    channel: Mapped[str] = mapped_column(String(10))  # email | sms | whatsapp
    purpose: Mapped[str] = mapped_column(String(10), default="login")  # login | link
    user_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)  # preenchido em purpose=link
    code_hash: Mapped[str] = mapped_column(String(64))
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    consumed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: timeutil.utcnow())


class Product(Base):
    __tablename__ = "products"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    type: Mapped[str] = mapped_column(String(30), index=True)
    occasion: Mapped[str] = mapped_column(String(60), index=True)
    theme: Mapped[str] = mapped_column(String(60), index=True)
    price_cents: Mapped[int] = mapped_column(Integer)
    featured: Mapped[bool] = mapped_column(Boolean, default=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    demo: Mapped[bool] = mapped_column(Boolean, default=False)  # catálogo de demonstração: não vende em produção
    file_key: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)  # arquivo do kit (entrega: a definir)
    search_text: Mapped[str] = mapped_column(Text, default="")  # nome/tema/ocasião sem acento, para a busca
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: timeutil.utcnow())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: timeutil.utcnow(),
                                                 onupdate=lambda: timeutil.utcnow())


class Cart(Base):
    __tablename__ = "carts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[Optional[str]] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True,
                                                   nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: timeutil.utcnow())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: timeutil.utcnow(),
                                                 onupdate=lambda: timeutil.utcnow())

    items: Mapped[List["CartItem"]] = relationship(back_populates="cart", cascade="all, delete-orphan",
                                                   order_by="CartItem.added_at")


class CartItem(Base):
    """Kits digitais: cada produto entra no máximo uma vez no carrinho (não há quantidade)."""
    __tablename__ = "cart_items"
    __table_args__ = (UniqueConstraint("cart_id", "product_id", name="uq_cart_product"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    cart_id: Mapped[str] = mapped_column(ForeignKey("carts.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"))
    added_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: timeutil.utcnow())

    cart: Mapped[Cart] = relationship(back_populates="items")
    product: Mapped[Product] = relationship()


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (UniqueConstraint("user_id", "idempotency_key", name="uq_order_idempotency"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    code: Mapped[str] = mapped_column(String(12), unique=True, default=new_order_code)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[str] = mapped_column(String(12), default="pending", index=True)  # pending|paid|failed|expired|canceled|refunded
    subtotal_cents: Mapped[int] = mapped_column(Integer)
    discount_cents: Mapped[int] = mapped_column(Integer, default=0)
    discount_code: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    total_cents: Mapped[int] = mapped_column(Integer)  # subtotal - desconto (sem juros de parcelamento)
    charged_cents: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # total cobrado, com juros se houver
    payment_method: Mapped[str] = mapped_column(String(10))
    installments: Mapped[int] = mapped_column(Integer, default=1)
    # dados de quem paga. O CPF completo vai só para o gateway; aqui ficam o hash (anti-abuso do desconto) e a máscara.
    payer_name: Mapped[str] = mapped_column(String(120))
    payer_email: Mapped[str] = mapped_column(String(254))
    payer_phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    payer_cpf_hash: Mapped[str] = mapped_column(String(64), index=True)
    payer_cpf_masked: Mapped[str] = mapped_column(String(20))
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: timeutil.utcnow())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: timeutil.utcnow(),
                                                 onupdate=lambda: timeutil.utcnow())

    items: Mapped[List["OrderItem"]] = relationship(back_populates="order", cascade="all, delete-orphan")
    payments: Mapped[List["Payment"]] = relationship(back_populates="order", cascade="all, delete-orphan",
                                                     order_by="Payment.created_at")


class OrderItem(Base):
    __tablename__ = "order_items"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    name: Mapped[str] = mapped_column(String(200))  # nome e preço no momento da compra
    unit_price_cents: Mapped[int] = mapped_column(Integer)

    order: Mapped[Order] = relationship(back_populates="items")
    product: Mapped[Product] = relationship()


class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = (UniqueConstraint("provider", "provider_payment_id", name="uq_payment_provider_id"),
                      Index("ix_payments_order", "order_id"))
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"))
    provider: Mapped[str] = mapped_column(String(20))
    provider_payment_id: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    method: Mapped[str] = mapped_column(String(10))
    status: Mapped[str] = mapped_column(String(12), default="pending")  # pending|approved|rejected|cancelled|expired|refunded|failed
    status_detail: Mapped[str] = mapped_column(String(120), default="")
    amount_cents: Mapped[int] = mapped_column(Integer)
    installments: Mapped[int] = mapped_column(Integer, default=1)
    total_paid_cents: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    pix_qr_code: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    pix_qr_code_base64: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    pix_ticket_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    boleto_barcode: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    boleto_digitable_line: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    boleto_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_checked_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: timeutil.utcnow())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: timeutil.utcnow(),
                                                 onupdate=lambda: timeutil.utcnow())

    order: Mapped[Order] = relationship(back_populates="payments")


class WebhookEvent(Base):
    """Registro de avisos recebidos dos gateways (auditoria e para evitar processar duas vezes o mesmo aviso)."""
    __tablename__ = "webhook_events"
    __table_args__ = (UniqueConstraint("provider", "event_key", name="uq_webhook_event"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    provider: Mapped[str] = mapped_column(String(20))
    event_key: Mapped[str] = mapped_column(String(200))
    received_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: timeutil.utcnow())
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
