"""Contas: cadastro, login (senha, Google, Facebook), sessões (access + refresh) e vínculos."""
import logging
from datetime import timedelta
from typing import Dict, Optional, Tuple

from sqlalchemy import or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import security, timeutil
from ..config import Settings
from ..errors import ApiError, bad_request, conflict, unauthorized
from ..models import Identity, RefreshToken, User
from ..schemas import TokenOut, UserOut
from ..validators import normalize_email, normalize_phone
from . import pricing

log = logging.getLogger("cm.accounts")


def user_out(user: User) -> UserOut:
    return UserOut(id=user.id, name=user.name, email=user.email, phone=user.phone, email_verified=user.email_verified,
                   phone_verified=user.phone_verified, providers=sorted(i.provider for i in user.identities),
                   has_password=bool(user.password_hash), created_at=user.created_at)


# ---------- sessões ----------
def issue_tokens(db: Session, s: Settings, user: User, is_new: bool = False) -> TokenOut:
    now = timeutil.utcnow()
    user.last_login_at = now
    access, expires_in = security.create_access_token(user.id, s)
    refresh = security.new_refresh_token()
    db.add(RefreshToken(user_id=user.id, token_hash=security.sha256_hex(refresh),
                        expires_at=now + timedelta(days=s.refresh_token_days)))
    db.commit()
    db.refresh(user)
    return TokenOut(access_token=access, refresh_token=refresh, expires_in=expires_in, user=user_out(user),
                    is_new_user=is_new, first_purchase_discount=pricing.discount_info(db, s, user, 0))


def revoke_all_refresh_tokens(db: Session, user_id: str) -> None:
    db.execute(update(RefreshToken).where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
               .values(revoked_at=timeutil.utcnow()))


def refresh_session(db: Session, s: Settings, refresh_token: str) -> TokenOut:
    """Troca o refresh token por um novo par (rotação). Reutilizar um token já usado derruba todas as sessões."""
    row = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == security.sha256_hex(refresh_token)))
    if row is None:
        raise unauthorized("Sessão inválida. Entre novamente.", "token_invalid")
    if row.revoked_at is not None:
        revoke_all_refresh_tokens(db, row.user_id)  # alguém reutilizou um token antigo: possível roubo
        db.commit()
        raise unauthorized("Sessão inválida. Entre novamente.", "token_reused")
    if row.expires_at < timeutil.utcnow():
        raise unauthorized("Sua sessão expirou. Entre novamente.", "token_expired")
    user = db.get(User, row.user_id)
    if user is None or not user.is_active:
        raise unauthorized("Conta indisponível.", "account_disabled")
    row.revoked_at = timeutil.utcnow()
    return issue_tokens(db, s, user)


def logout(db: Session, refresh_token: str) -> None:
    row = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == security.sha256_hex(refresh_token)))
    if row is not None and row.revoked_at is None:
        row.revoked_at = timeutil.utcnow()
        db.commit()


# ---------- e-mail / telefone + senha ----------
def register(db: Session, s: Settings, name: str, email: Optional[str], phone: Optional[str], password: str) -> TokenOut:
    taken = {}
    if email and db.scalar(select(User.id).where(User.email == email)):
        taken["email"] = "Este e-mail já tem cadastro. Entre ou recupere o acesso."
    if phone and db.scalar(select(User.id).where(User.phone == phone)):
        taken["phone"] = "Este telefone já tem cadastro. Entre ou recupere o acesso."
    if taken:
        raise ApiError(409, "account_exists", "Já existe uma conta com esse contato.", fields=taken)
    user = User(name=name, email=email, phone=phone, password_hash=security.hash_password(password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise conflict("Já existe uma conta com esse contato.", "account_exists")
    return issue_tokens(db, s, user, is_new=True)


def _identifier_to_filter(identifier: str):
    ident = identifier.strip()
    if "@" in ident:
        return User.email == normalize_email(ident)
    return User.phone == normalize_phone(ident)


def login_password(db: Session, s: Settings, identifier: str, password: str) -> TokenOut:
    generic = unauthorized("E-mail/telefone ou senha incorretos.", "invalid_credentials")
    try:
        flt = _identifier_to_filter(identifier)
    except ValueError:
        security.burn_password_time(password)
        raise generic
    user = db.scalar(select(User).where(flt))
    if user is None or not user.password_hash:
        security.burn_password_time(password)
        raise generic
    if not security.verify_password(password, user.password_hash):
        raise generic
    if not user.is_active:
        raise unauthorized("Conta indisponível.", "account_disabled")
    return issue_tokens(db, s, user)


# ---------- login social ----------
def _social_user(db: Session, provider: str, info: Dict[str, object]) -> Tuple[User, bool]:
    sub = str(info["sub"])
    ident = db.scalar(select(Identity).where(Identity.provider == provider, Identity.provider_user_id == sub))
    if ident is not None:
        return ident.user, False

    email = None
    if info.get("email"):
        try:
            email = normalize_email(str(info["email"]))
        except ValueError:
            email = None
    verified = bool(info.get("email_verified"))
    existing = db.scalar(select(User).where(User.email == email)) if email else None

    if existing is not None:
        if provider == "google" and verified:
            if not existing.email_verified:
                # Defesa contra "pré-cadastro": quem criou a conta com este e-mail sem prová-lo perde a senha.
                existing.password_hash = None
                existing.email_verified = True
                revoke_all_refresh_tokens(db, existing.id)
            db.add(Identity(user_id=existing.id, provider=provider, provider_user_id=sub, email=email))
            db.commit()
            db.refresh(existing)
            return existing, False
        raise ApiError(409, "account_exists_link_required",
                       "Já existe uma conta com este e-mail. Entre com ela e vincule este login em Minha conta.")

    user = User(name=str(info.get("name") or ""), email=email, email_verified=verified and provider == "google")
    db.add(user)
    db.flush()
    db.add(Identity(user_id=user.id, provider=provider, provider_user_id=sub, email=email))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise conflict("Não foi possível concluir o cadastro. Tente de novo.", "account_exists")
    db.refresh(user)
    return user, True


def login_social(db: Session, s: Settings, provider: str, info: Dict[str, object]) -> TokenOut:
    user, is_new = _social_user(db, provider, info)
    if not user.is_active:
        raise unauthorized("Conta indisponível.", "account_disabled")
    return issue_tokens(db, s, user, is_new=is_new)


def link_social(db: Session, user: User, provider: str, info: Dict[str, object]) -> User:
    """Vincula Google/Facebook a uma conta já logada."""
    sub = str(info["sub"])
    other = db.scalar(select(Identity).where(Identity.provider == provider, Identity.provider_user_id == sub))
    if other is not None:
        if other.user_id == user.id:
            return user
        raise conflict("Esta conta do " + provider.capitalize() + " já está ligada a outro cadastro.", "identity_in_use")
    if any(i.provider == provider for i in user.identities):
        raise conflict("Sua conta já tem um login do " + provider.capitalize() + " vinculado.", "provider_already_linked")
    db.add(Identity(user_id=user.id, provider=provider, provider_user_id=sub, email=info.get("email")))
    db.commit()
    db.refresh(user)
    return user


# ---------- contato verificado (OTP) ----------
def user_by_contact(db: Session, email: Optional[str], phone: Optional[str]) -> Optional[User]:
    conds = []
    if email:
        conds.append(User.email == email)
    if phone:
        conds.append(User.phone == phone)
    return db.scalar(select(User).where(or_(*conds))) if conds else None
