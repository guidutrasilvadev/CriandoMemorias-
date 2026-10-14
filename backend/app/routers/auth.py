"""Entrar e cadastrar: e-mail/telefone com senha, código (e-mail, SMS, WhatsApp), Google e Facebook."""
from typing import Optional

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from .. import security
from ..config import Settings, get_settings
from ..db import get_db
from ..deps import current_user_optional, rate_limit
from ..fmt import brl
from ..models import User
from ..schemas import (Benefit, BenefitsOut, FacebookIn, GoogleIn, LoginIn, OtpRequestIn, OtpVerifyIn, RefreshIn,
                       RegisterIn, TokenOut)
from ..services import accounts, otp, social

router = APIRouter(prefix="/auth", tags=["Entrar e cadastrar"])


def build_benefits(s: Settings) -> BenefitsOut:
    benefits = []
    pct = s.first_purchase_discount_percent
    if pct > 0:
        pct_text = f"{pct:g}".replace(".", ",")
        benefits.append(Benefit(
            id="first_purchase_discount", title=f"{pct_text}% de desconto na primeira compra",
            description="Entre com a sua conta e o desconto aparece no carrinho, aplicado ao seu primeiro pedido pago."))
    benefits.append(Benefit(id="saved_cart", title="Carrinho guardado",
                            description="Seus kits escolhidos ficam salvos e acompanham você em qualquer aparelho."))
    benefits.append(Benefit(id="orders_library", title="Pedidos e kits em um só lugar",
                            description="Acompanhe o pagamento e encontre o que você comprou quando quiser."))
    providers = []
    if s.google_client_id:
        providers.append("google")
    if s.facebook_app_id and s.facebook_app_secret:
        providers.append("facebook")
    providers += ["email", "phone"]
    fine = "Desconto válido uma vez por pessoa, na primeira compra paga."
    if pct > 0 and s.first_purchase_discount_max_cents > 0:
        fine = fine[:-1] + f", limitado a {brl(s.first_purchase_discount_max_cents)}."
    return BenefitsOut(headline="Entre para comprar com mais vantagens", benefits=benefits, providers=providers,
                       fine_print=fine if pct > 0 else "")


@router.get("/benefits", response_model=BenefitsOut, summary="Benefícios para mostrar na tela de login")
def benefits(s: Settings = Depends(get_settings)):
    return build_benefits(s)


@router.post("/register", response_model=TokenOut, status_code=201, summary="Criar conta com e-mail ou telefone e senha",
             dependencies=[Depends(rate_limit("register", 10, 3600))])
def register(body: RegisterIn, db: Session = Depends(get_db), s: Settings = Depends(get_settings)):
    return accounts.register(db, s, body.name, body.email, body.phone, body.password)


@router.post("/login", response_model=TokenOut, summary="Entrar com e-mail ou telefone e senha",
             dependencies=[Depends(rate_limit("login", 10, 900))])
def login(body: LoginIn, request: Request, db: Session = Depends(get_db), s: Settings = Depends(get_settings)):
    if s.rate_limit_enabled:  # também limita por conta, para não adiantar trocar de IP
        security.limiter.hit(f"login-id:{body.identifier.strip().lower()}", 8, 900)
    return accounts.login_password(db, s, body.identifier, body.password)


@router.post("/otp/request", summary="Pedir código por e-mail, SMS ou WhatsApp",
             dependencies=[Depends(rate_limit("otp-request", 10, 3600))])
def otp_request(body: OtpRequestIn, db: Session = Depends(get_db), s: Settings = Depends(get_settings),
                user: Optional[User] = Depends(current_user_optional)):
    """Cria a conta se ainda não existir (login sem senha). Em desenvolvimento a resposta traz `dev_code`."""
    return otp.request_code(db, s, body.destination, body.channel, body.purpose, user)


@router.post("/otp/verify", summary="Confirmar o código e entrar (ou vincular o contato)",
             dependencies=[Depends(rate_limit("otp-verify", 15, 600))])
def otp_verify(body: OtpVerifyIn, db: Session = Depends(get_db), s: Settings = Depends(get_settings)):
    user, is_new, purpose = otp.verify_code(db, s, body.destination, body.code, body.name)
    if purpose == "link":
        return {"linked": True, "user": accounts.user_out(user)}
    return accounts.issue_tokens(db, s, user, is_new=is_new)


@router.post("/google", response_model=TokenOut, summary="Entrar com Google",
             dependencies=[Depends(rate_limit("social", 30, 600))])
def google(body: GoogleIn, db: Session = Depends(get_db), s: Settings = Depends(get_settings)):
    info = social.verify_google_id_token(body.id_token, s)
    return accounts.login_social(db, s, "google", info)


@router.post("/facebook", response_model=TokenOut, summary="Entrar com Facebook",
             dependencies=[Depends(rate_limit("social", 30, 600))])
def facebook(body: FacebookIn, db: Session = Depends(get_db), s: Settings = Depends(get_settings)):
    info = social.verify_facebook_token(body.access_token, s)
    return accounts.login_social(db, s, "facebook", info)


@router.post("/refresh", response_model=TokenOut, summary="Renovar a sessão",
             dependencies=[Depends(rate_limit("refresh", 60, 600))])
def refresh(body: RefreshIn, db: Session = Depends(get_db), s: Settings = Depends(get_settings)):
    return accounts.refresh_session(db, s, body.refresh_token)


@router.post("/logout", status_code=204, summary="Sair (encerra o refresh token)")
def logout(body: RefreshIn, db: Session = Depends(get_db)):
    accounts.logout(db, body.refresh_token)
