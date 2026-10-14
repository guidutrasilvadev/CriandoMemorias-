"""Login e vínculo por código de 6 dígitos enviado por e-mail, SMS ou WhatsApp."""
import logging
import secrets
from datetime import timedelta
from typing import Dict, Optional, Tuple

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import security, timeutil
from ..config import Settings
from ..errors import ApiError, bad_request, conflict
from ..models import OtpCode, User
from ..validators import normalize_email, normalize_phone
from . import accounts
from .senders import ConsoleSender, SendError, get_sender

log = logging.getLogger("cm.otp")

COOLDOWN_SECONDS = 60
MAX_PER_DAY = 5
MAX_ATTEMPTS = 5


def _normalize_destination(raw: str, channel: str) -> str:
    try:
        return normalize_email(raw) if channel == "email" else normalize_phone(raw)
    except ValueError as exc:
        raise bad_request(str(exc), "invalid_destination", {"destination": str(exc)})


def _code_hash(s: Settings, destination: str, code: str) -> str:
    return security.hmac_hex(s.secret_key, f"otp:{destination}:{code}")


def request_code(db: Session, s: Settings, destination_raw: str, channel: str, purpose: str,
                 user: Optional[User]) -> Dict[str, object]:
    destination = _normalize_destination(destination_raw, channel)
    if purpose == "link":
        if user is None:
            raise ApiError(401, "unauthorized", "Entre na sua conta para adicionar um contato.")
        owner = accounts.user_by_contact(db, destination if channel == "email" else None,
                                         destination if channel != "email" else None)
        if owner is not None and owner.id != user.id:
            raise conflict("Este contato já está em uso por outra conta.", "contact_in_use")

    now = timeutil.utcnow()
    last = db.scalar(select(func.max(OtpCode.created_at)).where(OtpCode.destination == destination))
    if last is not None and (now - last).total_seconds() < COOLDOWN_SECONDS:
        wait = COOLDOWN_SECONDS - int((now - last).total_seconds())
        raise ApiError(429, "otp_cooldown", f"Aguarde {wait}s para pedir um novo código.",
                       headers={"Retry-After": str(wait)})
    sent_today = db.scalar(select(func.count()).select_from(OtpCode).where(
        OtpCode.destination == destination, OtpCode.created_at > now - timedelta(hours=24))) or 0
    if sent_today >= MAX_PER_DAY:
        raise ApiError(429, "otp_daily_limit", "Você atingiu o limite de códigos de hoje. Tente amanhã.")

    sender = get_sender(channel, s)
    code = f"{secrets.randbelow(10 ** 6):06d}"
    db.execute(update(OtpCode).where(OtpCode.destination == destination, OtpCode.consumed_at.is_(None))
               .values(consumed_at=now))  # só o código mais recente vale
    db.add(OtpCode(destination=destination, channel=channel, purpose=purpose, user_id=user.id if user else None,
                   code_hash=_code_hash(s, destination, code), expires_at=now + timedelta(minutes=s.otp_ttl_minutes)))
    db.commit()
    try:
        sender.send(channel, destination, code, s.otp_ttl_minutes)
    except SendError:
        raise ApiError(502, "otp_send_failed", "Não conseguimos enviar o código agora. Tente em instantes.")
    out: Dict[str, object] = {"sent": True, "expires_in": s.otp_ttl_minutes * 60}
    if s.otp_dev_echo and not s.is_production and isinstance(sender, ConsoleSender):
        out["dev_code"] = code  # só em desenvolvimento, para testar sem e-mail/SMS de verdade
    return out


def verify_code(db: Session, s: Settings, destination_raw: str, code: str, name: Optional[str]
                ) -> Tuple[User, bool, str]:
    """Confere o código. Devolve (usuário, é_novo, propósito). Em 'link' o contato é adicionado a quem pediu o código."""
    destination = _normalize_destination(destination_raw, "email" if "@" in destination_raw else "sms")
    row = db.scalar(select(OtpCode).where(OtpCode.destination == destination, OtpCode.consumed_at.is_(None))
                    .order_by(OtpCode.created_at.desc()))
    invalid = bad_request("Código inválido ou expirado. Peça um novo.", "otp_invalid")
    now = timeutil.utcnow()
    if row is None or row.expires_at < now:
        raise invalid
    row.attempts += 1
    if row.attempts > MAX_ATTEMPTS:
        row.consumed_at = now
        db.commit()
        raise invalid
    if not secrets.compare_digest(row.code_hash, _code_hash(s, destination, code)):
        db.commit()
        raise bad_request("Código incorreto.", "otp_wrong")
    row.consumed_at = now

    is_email = "@" in destination
    if row.purpose == "link":
        user = db.get(User, row.user_id) if row.user_id else None
        if user is None:
            raise invalid
        owner = accounts.user_by_contact(db, destination if is_email else None, None if is_email else destination)
        if owner is not None and owner.id != user.id:
            db.commit()
            raise conflict("Este contato já está em uso por outra conta.", "contact_in_use")
        if is_email:
            user.email, user.email_verified = destination, True
        else:
            user.phone, user.phone_verified = destination, True
        db.commit()
        return user, False, "link"

    user = accounts.user_by_contact(db, destination if is_email else None, None if is_email else destination)
    is_new = user is None
    if is_new:
        user = User(name=(name or "").strip(), email=destination if is_email else None,
                    phone=None if is_email else destination, email_verified=is_email, phone_verified=not is_email)
        db.add(user)
    elif is_email:
        user.email_verified = True
    else:
        user.phone_verified = True
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise conflict("Não foi possível concluir o acesso. Tente de novo.", "account_exists")
    db.refresh(user)
    return user, is_new, "login"
