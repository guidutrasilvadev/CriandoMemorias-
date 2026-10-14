"""Formatos de entrada e saída da API (aparecem na documentação interativa em /docs)."""
from datetime import date, datetime
from typing import Annotated, List, Literal, Optional

from pydantic import BaseModel, Field, PlainSerializer, field_validator, model_validator

from . import validators as v

UtcDateTime = Annotated[datetime, PlainSerializer(lambda d: d.isoformat(timespec="seconds") + "Z", return_type=str)]


# ---------- entrada: conta ----------
class RegisterIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: Optional[str] = None
    phone: Optional[str] = None
    password: str = Field(min_length=8, max_length=128)

    @field_validator("name")
    @classmethod
    def _name(cls, x: str) -> str:
        x = " ".join(x.split())
        if not x:
            raise ValueError("Informe seu nome.")
        return x

    @field_validator("email")
    @classmethod
    def _email(cls, x: Optional[str]) -> Optional[str]:
        return v.normalize_email(x) if x else None

    @field_validator("phone")
    @classmethod
    def _phone(cls, x: Optional[str]) -> Optional[str]:
        return v.normalize_phone(x) if x else None

    @model_validator(mode="after")
    def _one_contact(self):
        if not self.email and not self.phone:
            raise ValueError("Informe e-mail ou telefone.")
        return self


class LoginIn(BaseModel):
    identifier: str = Field(min_length=3, max_length=254, description="E-mail ou telefone")
    password: str = Field(min_length=1, max_length=128)


class OtpRequestIn(BaseModel):
    destination: str = Field(min_length=3, max_length=254, description="E-mail ou telefone que vai receber o código")
    channel: Literal["email", "sms", "whatsapp"]
    purpose: Literal["login", "link"] = Field("login", description="'link' adiciona o contato à conta logada")


class OtpVerifyIn(BaseModel):
    destination: str = Field(min_length=3, max_length=254)
    code: str = Field(pattern=r"^\d{6}$")
    name: Optional[str] = Field(None, max_length=120, description="Opcional: nome, ao criar a conta")


class GoogleIn(BaseModel):
    id_token: str = Field(min_length=20, description="ID token entregue pelo botão 'Entrar com Google' (Google Identity Services)")


class FacebookIn(BaseModel):
    access_token: str = Field(min_length=10, description="Token entregue pelo Facebook Login no navegador")


class RefreshIn(BaseModel):
    refresh_token: str = Field(min_length=20)


class ProfileUpdateIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)


# ---------- entrada: carrinho e checkout ----------
class CartAddIn(BaseModel):
    product_id: int = Field(ge=1)


class AddressIn(BaseModel):
    zip_code: str
    street: str = Field(min_length=2, max_length=120)
    number: str = Field(min_length=1, max_length=20)
    complement: str = Field("", max_length=80)
    neighborhood: str = Field(min_length=2, max_length=80)
    city: str = Field(min_length=2, max_length=80)
    state: str

    @field_validator("zip_code")
    @classmethod
    def _cep(cls, x: str) -> str:
        return v.normalize_cep(x)

    @field_validator("state")
    @classmethod
    def _uf(cls, x: str) -> str:
        return v.normalize_uf(x)


class PayerIn(BaseModel):
    name: str = Field(min_length=3, max_length=120)
    email: str
    cpf: str
    phone: Optional[str] = None
    address: Optional[AddressIn] = Field(None, description="Obrigatório para boleto")

    @field_validator("name")
    @classmethod
    def _name(cls, x: str) -> str:
        x = " ".join(x.split())
        if len(x.split()) < 2:
            raise ValueError("Informe nome e sobrenome.")
        return x

    @field_validator("email")
    @classmethod
    def _email(cls, x: str) -> str:
        return v.normalize_email(x)

    @field_validator("cpf")
    @classmethod
    def _cpf(cls, x: str) -> str:
        if not v.is_valid_cpf(x):
            raise ValueError("CPF inválido.")
        return v.only_digits(x)

    @field_validator("phone")
    @classmethod
    def _phone(cls, x: Optional[str]) -> Optional[str]:
        return v.normalize_phone(x) if x else None


class CheckoutIn(BaseModel):
    payment_method: Literal["pix", "boleto", "card"]
    installments: int = Field(1, ge=1, le=24, description="Só para cartão; Pix e boleto são sempre 1")
    card_token: Optional[str] = Field(None, max_length=200, description="Token do cartão gerado no navegador pelo SDK da operadora")
    card_brand: Optional[str] = Field(None, max_length=40, description="Bandeira/identificador do cartão na operadora (ex.: visa, master)")
    expected_total_cents: Optional[int] = Field(None, ge=1, description="O total que a tela mostrou (no cartão parcelado, já com juros). "
                                                "Se o servidor chegar a outro valor (ex.: o desconto não vale para este CPF), nada é cobrado: volta 409 price_changed")
    payer: PayerIn

    @model_validator(mode="after")
    def _by_method(self):
        if self.payment_method == "card":
            if not self.card_token or not self.card_brand:
                raise ValueError("Para cartão, envie card_token e card_brand.")
        else:
            self.installments = 1
        if self.payment_method == "boleto" and self.payer.address is None:
            raise ValueError("Para boleto, informe o endereço de quem paga.")
        return self


# ---------- saída ----------
class UserOut(BaseModel):
    id: str
    name: str
    email: Optional[str]
    phone: Optional[str]
    email_verified: bool
    phone_verified: bool
    providers: List[str]
    has_password: bool
    created_at: UtcDateTime


class DiscountInfo(BaseModel):
    code: str = "PRIMEIRA_COMPRA"
    percent: float
    status: Literal["login_required", "eligible", "used", "disabled"]
    estimated_amount_cents: int = 0


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Segundos até o access_token expirar")
    user: UserOut
    is_new_user: bool
    first_purchase_discount: DiscountInfo


class Benefit(BaseModel):
    id: str
    title: str
    description: str


class BenefitsOut(BaseModel):
    headline: str
    benefits: List[Benefit]
    providers: List[str]
    fine_print: str


class ProductOut(BaseModel):
    id: int
    slug: str
    name: str
    type: str
    type_label: str
    type_group: str
    occasion: str
    theme: str
    price_cents: int
    featured: bool
    demo: bool


class ProductPage(BaseModel):
    items: List[ProductOut]
    total: int
    page: int
    page_size: int


class FacetCount(BaseModel):
    value: str
    label: str
    count: int


class FacetsOut(BaseModel):
    occasions: List[FacetCount]
    type_groups: List[FacetCount]
    themes: List[FacetCount]
    price_min_cents: int
    price_max_cents: int
    total: int


class InstallmentOption(BaseModel):
    installments: int
    installment_cents: int
    total_cents: int
    interest_free: bool


class CartItemOut(BaseModel):
    product: ProductOut
    added_at: UtcDateTime


class CartOut(BaseModel):
    cart_id: Optional[str]
    items: List[CartItemOut]
    items_count: int
    subtotal_cents: int
    discount_cents: int
    total_cents: int
    first_purchase_discount: DiscountInfo
    installment_options: List[InstallmentOption]
    unavailable_product_ids: List[int] = []


class PixOut(BaseModel):
    qr_code: Optional[str] = Field(description="Texto do Pix 'copia e cola'")
    qr_code_base64: Optional[str] = Field(description="Imagem PNG do QR Code em base64 (quando a operadora envia)")
    ticket_url: Optional[str]
    expires_at: Optional[UtcDateTime]


class BoletoOut(BaseModel):
    barcode: Optional[str]
    digitable_line: Optional[str]
    url: Optional[str]
    due_date: Optional[date]


class PaymentOut(BaseModel):
    id: str
    provider: str
    method: str
    status: str
    status_detail: str
    amount_cents: int
    installments: int
    total_paid_cents: Optional[int]
    pix: Optional[PixOut] = None
    boleto: Optional[BoletoOut] = None


class OrderItemOut(BaseModel):
    product_id: int
    name: str
    unit_price_cents: int


class OrderOut(BaseModel):
    id: str
    code: str
    status: Literal["pending", "paid", "failed", "expired", "canceled", "refunded"]
    items: List[OrderItemOut]
    subtotal_cents: int
    discount_cents: int
    discount_code: Optional[str]
    total_cents: int
    charged_cents: Optional[int]
    payment_method: str
    installments: int
    payment: Optional[PaymentOut]
    created_at: UtcDateTime
    expires_at: Optional[UtcDateTime]
    paid_at: Optional[UtcDateTime]


class LibraryItemOut(BaseModel):
    product: ProductOut
    order_id: str
    order_code: str
    purchased_at: UtcDateTime
    download_available: bool


# ---------- administração ----------
class ProductIn(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    slug: Optional[str] = Field(None, max_length=160)
    type: str
    occasion: str = Field(min_length=2, max_length=60)
    theme: str = Field(min_length=2, max_length=60)
    price_cents: int = Field(ge=1)
    featured: bool = False
    active: bool = True
    demo: bool = False
    file_key: Optional[str] = Field(None, max_length=300)
    id: Optional[int] = Field(None, ge=1, description="Opcional; ao importar, reaproveita o id")


class ProductPatch(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=200)
    type: Optional[str] = None
    occasion: Optional[str] = Field(None, min_length=2, max_length=60)
    theme: Optional[str] = Field(None, min_length=2, max_length=60)
    price_cents: Optional[int] = Field(None, ge=1)
    featured: Optional[bool] = None
    active: Optional[bool] = None
    demo: Optional[bool] = None
    file_key: Optional[str] = Field(None, max_length=300)
