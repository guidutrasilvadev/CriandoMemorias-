"""Configuração por variáveis de ambiente. Veja .env.example para a lista completa."""
import logging
import os
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import List

log = logging.getLogger("cm.config")

BACKEND_DIR = Path(__file__).resolve().parent.parent
DEV_SECRET = "dev-only-secret-troque-em-producao-0123456789abcdef"


def load_dotenv(path: Path = BACKEND_DIR / ".env") -> None:
    """Lê KEY=VALUE de um arquivo .env, sem sobrescrever o que já está no ambiente."""
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        value = value.strip()
        if value[:1] in ('"', "'"):  # entre aspas vale tudo até a aspa que fecha (inclusive um #)
            end = value.find(value[0], 1)
            value = value[1:end] if end != -1 else value[1:]
        else:  # sem aspas, " # comentário" no fim da linha não faz parte do valor
            value = re.split(r"\s+#", value, maxsplit=1)[0].strip()
        os.environ.setdefault(key.strip(), value)


def _s(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def _i(name: str, default: int) -> int:
    v = _s(name)
    return int(v) if v else default


def _f(name: str, default: float) -> float:
    v = _s(name)
    return float(v.replace(",", ".")) if v else default


def _b(name: str, default: bool) -> bool:
    v = _s(name).lower()
    return default if not v else v in ("1", "true", "sim", "yes", "on")


def _list(name: str, default: str = "") -> List[str]:
    return [x.strip() for x in _s(name, default).split(",") if x.strip()]


@dataclass(frozen=True)
class Settings:
    env: str
    database_url: str
    secret_key: str
    access_token_minutes: int
    refresh_token_days: int
    cors_origins: List[str]
    trust_proxy: bool
    rate_limit_enabled: bool
    admin_api_key: str
    # login social
    google_client_id: str
    facebook_app_id: str
    facebook_app_secret: str
    # pagamentos
    payment_gateway: str
    public_api_url: str
    mercadopago_access_token: str
    mercadopago_public_key: str
    mercadopago_webhook_secret: str
    simulated_webhook_secret: str
    allow_demo_checkout: bool
    min_order_cents: int
    pix_expiration_minutes: int
    boleto_due_days: int
    card_order_expiration_minutes: int
    # parcelamento (cartão)
    max_installments: int
    interest_free_installments: int
    monthly_interest_percent: float
    min_installment_cents: int
    # desconto de primeira compra
    first_purchase_discount_percent: float
    first_purchase_discount_max_cents: int
    # código de verificação (e-mail, SMS, WhatsApp)
    otp_ttl_minutes: int
    otp_dev_echo: bool
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_password: str
    smtp_from: str
    twilio_account_sid: str
    twilio_auth_token: str
    twilio_sms_from: str
    twilio_whatsapp_from: str
    # catálogo
    auto_seed_demo: bool
    # site estático servido pela própria API (só desenvolvimento)
    serve_site: bool

    @property
    def is_production(self) -> bool:
        return self.env == "production"


@lru_cache()
def get_settings() -> Settings:
    env = _s("ENV", "dev").lower()
    prod = env == "production"
    secret = _s("SECRET_KEY")
    gateway = _s("PAYMENT_GATEWAY", "simulated").lower()

    if prod:
        problems = []
        if len(secret) < 32:
            problems.append("SECRET_KEY (mínimo 32 caracteres)")
        if not _s("DATABASE_URL"):
            problems.append("DATABASE_URL")
        if not _list("CORS_ORIGINS"):
            problems.append("CORS_ORIGINS")
        if gateway == "simulated":
            problems.append("PAYMENT_GATEWAY diferente de 'simulated'")
        if gateway == "mercadopago" and not (_s("MERCADOPAGO_ACCESS_TOKEN") and _s("PUBLIC_API_URL")):
            problems.append("MERCADOPAGO_ACCESS_TOKEN e PUBLIC_API_URL")
        if problems:
            raise RuntimeError("Configuração de produção incompleta: " + "; ".join(problems))
    elif not secret:
        secret = DEV_SECRET
        log.warning("SECRET_KEY não definido: usando chave de desenvolvimento. Não use assim em produção.")

    default_db = "sqlite:///" + str(BACKEND_DIR / "data.nosync" / "loja.db")  # .nosync: o iCloud não sincroniza
    default_cors = "" if prod else "http://localhost:8000,http://127.0.0.1:8000,http://localhost:5500,http://127.0.0.1:5500,null"

    s = Settings(
        env=env,
        database_url=_s("DATABASE_URL", default_db),
        secret_key=secret,
        access_token_minutes=_i("ACCESS_TOKEN_MINUTES", 15),
        refresh_token_days=_i("REFRESH_TOKEN_DAYS", 30),
        cors_origins=_list("CORS_ORIGINS", default_cors),
        trust_proxy=_b("TRUST_PROXY", False),
        rate_limit_enabled=_b("RATE_LIMIT_ENABLED", True),
        admin_api_key=_s("ADMIN_API_KEY"),
        google_client_id=_s("GOOGLE_CLIENT_ID"),
        facebook_app_id=_s("FACEBOOK_APP_ID"),
        facebook_app_secret=_s("FACEBOOK_APP_SECRET"),
        payment_gateway=gateway,
        public_api_url=_s("PUBLIC_API_URL").rstrip("/"),
        mercadopago_access_token=_s("MERCADOPAGO_ACCESS_TOKEN"),
        mercadopago_public_key=_s("MERCADOPAGO_PUBLIC_KEY"),
        mercadopago_webhook_secret=_s("MERCADOPAGO_WEBHOOK_SECRET"),
        simulated_webhook_secret=_s("SIMULATED_WEBHOOK_SECRET", "dev-webhook-secret"),
        allow_demo_checkout=_b("ALLOW_DEMO_CHECKOUT", not prod),
        min_order_cents=_i("MIN_ORDER_CENTS", 500),
        pix_expiration_minutes=_i("PIX_EXPIRATION_MINUTES", 30),
        boleto_due_days=_i("BOLETO_DUE_DAYS", 3),
        card_order_expiration_minutes=_i("CARD_ORDER_EXPIRATION_MINUTES", 30),
        max_installments=_i("MAX_INSTALLMENTS", 6),
        interest_free_installments=_i("INTEREST_FREE_INSTALLMENTS", 6),
        monthly_interest_percent=_f("MONTHLY_INTEREST_PERCENT", 0.0),
        min_installment_cents=_i("MIN_INSTALLMENT_CENTS", 500),
        first_purchase_discount_percent=_f("FIRST_PURCHASE_DISCOUNT_PERCENT", 10.0),
        first_purchase_discount_max_cents=_i("FIRST_PURCHASE_DISCOUNT_MAX_CENTS", 0),
        otp_ttl_minutes=_i("OTP_TTL_MINUTES", 10),
        otp_dev_echo=_b("OTP_DEV_ECHO", not prod),
        smtp_host=_s("SMTP_HOST"),
        smtp_port=_i("SMTP_PORT", 587),
        smtp_user=_s("SMTP_USER"),
        smtp_password=_s("SMTP_PASSWORD"),
        smtp_from=_s("SMTP_FROM"),
        twilio_account_sid=_s("TWILIO_ACCOUNT_SID"),
        twilio_auth_token=_s("TWILIO_AUTH_TOKEN"),
        twilio_sms_from=_s("TWILIO_SMS_FROM"),
        twilio_whatsapp_from=_s("TWILIO_WHATSAPP_FROM"),
        auto_seed_demo=_b("AUTO_SEED_DEMO", not prod),
        serve_site=_b("SERVE_SITE", not prod),
    )
    if not 0 <= s.first_purchase_discount_percent < 100:
        raise RuntimeError("FIRST_PURCHASE_DISCOUNT_PERCENT deve estar entre 0 e 99.")
    if s.max_installments < 1 or s.interest_free_installments < 0:
        raise RuntimeError("Parcelamento inválido: MAX_INSTALLMENTS >= 1 e INTEREST_FREE_INSTALLMENTS >= 0.")
    return s
