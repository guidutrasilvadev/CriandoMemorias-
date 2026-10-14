"""Envio do código de verificação: e-mail (SMTP), SMS e WhatsApp (Twilio) ou console (só em desenvolvimento)."""
import logging
import smtplib
import ssl
from email.message import EmailMessage

import httpx

from ..config import Settings
from ..errors import ApiError

log = logging.getLogger("cm.otp")


class SendError(Exception):
    pass


class ConsoleSender:
    """Não envia nada: escreve o código no log do servidor. Só existe fora de produção."""
    name = "console"

    def send(self, channel: str, destination: str, code: str, ttl_minutes: int) -> None:
        log.warning("[código de verificação] %s para %s: %s (vale %d min)", channel, destination, code, ttl_minutes)


def message_text(code: str, ttl_minutes: int) -> str:
    return (f"Seu código da Criando Memórias é {code}. Ele vale por {ttl_minutes} minutos. "
            "Se não foi você, ignore esta mensagem.")


class SmtpSender:
    name = "smtp"

    def __init__(self, s: Settings):
        self.s = s

    def send(self, channel: str, destination: str, code: str, ttl_minutes: int) -> None:
        msg = EmailMessage()
        msg["Subject"] = "Seu código de acesso — Criando Memórias"
        msg["From"] = self.s.smtp_from or self.s.smtp_user
        msg["To"] = destination
        msg.set_content(message_text(code, ttl_minutes))
        try:
            if self.s.smtp_port == 465:
                with smtplib.SMTP_SSL(self.s.smtp_host, 465, context=ssl.create_default_context(), timeout=15) as smtp:
                    self._login_and_send(smtp, msg)
            else:
                with smtplib.SMTP(self.s.smtp_host, self.s.smtp_port, timeout=15) as smtp:
                    smtp.starttls(context=ssl.create_default_context())
                    self._login_and_send(smtp, msg)
        except (smtplib.SMTPException, OSError) as exc:
            log.error("Falha ao enviar e-mail: %s", exc.__class__.__name__)
            raise SendError("e-mail")

    def _login_and_send(self, smtp: smtplib.SMTP, msg: EmailMessage) -> None:
        if self.s.smtp_user:
            smtp.login(self.s.smtp_user, self.s.smtp_password)
        smtp.send_message(msg)


class TwilioSender:
    name = "twilio"

    def __init__(self, s: Settings):
        self.s = s

    def send(self, channel: str, destination: str, code: str, ttl_minutes: int) -> None:
        wa = channel == "whatsapp"
        sender = self.s.twilio_whatsapp_from if wa else self.s.twilio_sms_from
        data = {"To": ("whatsapp:" if wa else "") + destination,
                "From": ("whatsapp:" if wa and not sender.startswith("whatsapp:") else "") + sender,
                "Body": message_text(code, ttl_minutes)}
        try:
            resp = httpx.post(f"https://api.twilio.com/2010-04-01/Accounts/{self.s.twilio_account_sid}/Messages.json",
                              data=data, auth=(self.s.twilio_account_sid, self.s.twilio_auth_token), timeout=15)
        except httpx.HTTPError as exc:
            log.error("Falha ao falar com a Twilio: %s", exc.__class__.__name__)
            raise SendError(channel)
        if resp.status_code >= 400:
            log.error("Twilio recusou o envio (%s)", resp.status_code)
            raise SendError(channel)


def get_sender(channel: str, s: Settings):
    if channel == "email" and s.smtp_host:
        return SmtpSender(s)
    if channel in ("sms", "whatsapp") and s.twilio_account_sid and (
            s.twilio_whatsapp_from if channel == "whatsapp" else s.twilio_sms_from):
        return TwilioSender(s)
    if not s.is_production:
        return ConsoleSender()
    raise ApiError(503, "otp_channel_unavailable", "Este meio de verificação ainda não está disponível.")
