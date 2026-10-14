"""Validação e normalização de e-mail, telefone, CPF e endereço (Brasil)."""
import re

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-']+@[A-Za-z0-9\-]+(\.[A-Za-z0-9\-]+)*\.[A-Za-z]{2,}$")
UFS = {"AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI",
       "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO"}


def only_digits(value: str) -> str:
    return re.sub(r"\D", "", value or "")


def normalize_email(value: str) -> str:
    v = (value or "").strip().lower()
    if len(v) > 254 or not EMAIL_RE.match(v):
        raise ValueError("E-mail inválido.")
    return v


def normalize_phone(value: str) -> str:
    """Devolve o telefone em formato internacional (+5511912345678). Sem "+", assume Brasil."""
    raw = (value or "").strip()
    digits = only_digits(raw)
    if raw.startswith("+"):
        if not 8 <= len(digits) <= 15:
            raise ValueError("Telefone inválido.")
        return "+" + digits
    if digits.startswith("55") and len(digits) in (12, 13):
        digits = digits[2:]
    if len(digits) not in (10, 11):
        raise ValueError("Telefone inválido. Use DDD + número.")
    ddd, number = digits[:2], digits[2:]
    if ddd[0] == "0" or ddd[1] == "0":
        raise ValueError("DDD inválido.")
    if len(number) == 9 and number[0] != "9":
        raise ValueError("Celular inválido.")
    if len(number) == 8 and number[0] == "0":
        raise ValueError("Telefone inválido.")
    return "+55" + digits


def is_valid_cpf(value: str) -> bool:
    cpf = only_digits(value)
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False
    for size in (9, 10):
        total = sum(int(cpf[i]) * (size + 1 - i) for i in range(size))
        digit = (total * 10) % 11 % 10
        if digit != int(cpf[size]):
            return False
    return True


def mask_cpf(value: str) -> str:
    cpf = only_digits(value)
    return f"***.{cpf[3:6]}.{cpf[6:9]}-**" if len(cpf) == 11 else "***"


def normalize_cep(value: str) -> str:
    cep = only_digits(value)
    if len(cep) != 8:
        raise ValueError("CEP inválido.")
    return cep


def normalize_uf(value: str) -> str:
    uf = (value or "").strip().upper()
    if uf not in UFS:
        raise ValueError("UF inválida.")
    return uf
