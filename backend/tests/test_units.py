"""Testes das regras isoladas: validações, desconto, parcelas e senhas."""
import os

import pytest

from app import validators as v
from app.config import get_settings
from app.fmt import brl
from app.security import hash_password, verify_password
from app.services import pricing


# ---------- validações ----------
@pytest.mark.parametrize("cpf,ok", [("529.982.247-25", True), ("52998224725", True), ("11144477735", True),
                                    ("111.111.111-11", False), ("52998224724", False), ("123", False), ("", False)])
def test_cpf(cpf, ok):
    assert v.is_valid_cpf(cpf) is ok


def test_mask_cpf():
    assert v.mask_cpf("529.982.247-25") == "***.982.247-**"


@pytest.mark.parametrize("raw,expected", [
    ("(11) 98765-4321", "+5511987654321"), ("11987654321", "+5511987654321"), ("+55 11 98765-4321", "+5511987654321"),
    ("5511987654321", "+5511987654321"), ("1133334444", "+551133334444"), ("+1 415 555 2671", "+14155552671")])
def test_phone_ok(raw, expected):
    assert v.normalize_phone(raw) == expected


@pytest.mark.parametrize("raw", ["", "123", "(00) 98765-4321", "11887654321", "abc", "+12"])
def test_phone_invalid(raw):
    with pytest.raises(ValueError):
        v.normalize_phone(raw)


def test_email():
    assert v.normalize_email("  Ana@Exemplo.COM ") == "ana@exemplo.com"
    for bad in ("sem-arroba", "a@b", "a b@c.com", ""):
        with pytest.raises(ValueError):
            v.normalize_email(bad)


def test_cep_uf():
    assert v.normalize_cep("01310-100") == "01310100"
    assert v.normalize_uf("sp") == "SP"
    with pytest.raises(ValueError):
        v.normalize_cep("123")
    with pytest.raises(ValueError):
        v.normalize_uf("XX")


def test_brl():
    assert brl(7490) == "R$ 74,90"
    assert brl(123456) == "R$ 1.234,56"
    assert brl(5) == "R$ 0,05"


# ---------- senhas ----------
def test_password_hash():
    h = hash_password("segredo-123")
    assert h.startswith("$argon2id$") and "segredo" not in h
    assert verify_password("segredo-123", h)
    assert not verify_password("errada", h)
    assert not verify_password("x", "lixo")


# ---------- desconto e parcelas ----------
def settings(monkeypatch, **env):
    for k, val in env.items():
        monkeypatch.setenv(k, str(val))
    get_settings.cache_clear()
    return get_settings()


def test_discount_percent_and_cap(monkeypatch):
    s = settings(monkeypatch, FIRST_PURCHASE_DISCOUNT_PERCENT=10)
    assert pricing.first_purchase_discount_cents(7490, s) == 749
    assert pricing.first_purchase_discount_cents(2990, s) == 299
    s = settings(monkeypatch, FIRST_PURCHASE_DISCOUNT_PERCENT=10, FIRST_PURCHASE_DISCOUNT_MAX_CENTS=500)
    assert pricing.first_purchase_discount_cents(7490, s) == 500
    s = settings(monkeypatch, FIRST_PURCHASE_DISCOUNT_PERCENT=0)
    assert pricing.first_purchase_discount_cents(7490, s) == 0


def test_installments_interest_free_with_minimum(monkeypatch):
    s = settings(monkeypatch, MAX_INSTALLMENTS=12, INTEREST_FREE_INSTALLMENTS=12, MIN_INSTALLMENT_CENTS=500)
    opts = pricing.installment_options(7490, s)
    assert [o.installments for o in opts] == list(range(1, 13))  # 7490/12 = 624 >= 500
    assert opts[2].installment_cents == 2497 and opts[2].total_cents == 7490 and opts[2].interest_free
    # valor pequeno: a parcela mínima corta as opções
    assert [o.installments for o in pricing.installment_options(1200, s)] == [1, 2]
    assert pricing.installment_options(0, s) == []


def test_installments_with_interest(monkeypatch):
    s = settings(monkeypatch, MAX_INSTALLMENTS=6, INTEREST_FREE_INSTALLMENTS=2, MONTHLY_INTEREST_PERCENT=2)
    opts = {o.installments: o for o in pricing.installment_options(10000, s)}
    assert opts[1].total_cents == 10000 and opts[2].total_cents == 10000 and opts[2].interest_free
    assert not opts[3].interest_free
    assert opts[3].installment_cents == 3468  # PMT de 10000 a 2% a.m. em 3x
    assert opts[3].total_cents == 3468 * 3 > 10000
    assert opts[6].total_cents > opts[3].total_cents


def test_dotenv_ignores_inline_comments_and_keeps_quoted_values(tmp_path, monkeypatch):
    """O dev.sh copia o .env.example, que tem comentário na mesma linha do valor: isso não pode quebrar a leitura."""
    from app.config import load_dotenv
    env = tmp_path / ".env"
    env.write_text("# comentário solto\n"
                   "ENV=dev                          # dev | production\n"
                   "MONTHLY_INTEREST_PERCENT=0       # juros ao mês (0 = sem juros)\n"
                   'SMTP_FROM="Criando Memórias <contato@exemplo.com.br>"   # remetente\n'
                   "NOTA='tem # dentro das aspas'\n"
                   "SEM_COMENTARIO=valor#colado\n"
                   "VAZIO=\n", encoding="utf-8")
    for k in ("ENV", "MONTHLY_INTEREST_PERCENT", "SMTP_FROM", "NOTA", "SEM_COMENTARIO", "VAZIO"):
        monkeypatch.delenv(k, raising=False)
    load_dotenv(env)
    assert os.environ["ENV"] == "dev" and os.environ["MONTHLY_INTEREST_PERCENT"] == "0"
    assert os.environ["SMTP_FROM"] == "Criando Memórias <contato@exemplo.com.br>"
    assert os.environ["NOTA"] == "tem # dentro das aspas" and os.environ["SEM_COMENTARIO"] == "valor#colado" and os.environ["VAZIO"] == ""
    for k in ("ENV", "MONTHLY_INTEREST_PERCENT", "SMTP_FROM", "NOTA", "SEM_COMENTARIO", "VAZIO"):
        os.environ.pop(k, None)


def test_env_example_loads_without_errors(tmp_path, monkeypatch):
    """O .env que o dev.sh cria na primeira vez (cópia do .env.example) precisa dar um Settings válido."""
    import shutil
    from pathlib import Path
    from app.config import get_settings, load_dotenv
    from tests.conftest import ENV_KEYS
    env = tmp_path / ".env"
    shutil.copy(Path(__file__).resolve().parent.parent / ".env.example", env)
    for k in ENV_KEYS:
        monkeypatch.delenv(k, raising=False)
    snapshot = dict(os.environ)
    try:
        load_dotenv(env)
        get_settings.cache_clear()
        s = get_settings()
        assert s.env == "dev" and s.payment_gateway == "simulated" and s.first_purchase_discount_percent == 10
        assert s.monthly_interest_percent == 0 and s.max_installments == 6 and s.serve_site is True
    finally:
        os.environ.clear(); os.environ.update(snapshot)
        get_settings.cache_clear()
