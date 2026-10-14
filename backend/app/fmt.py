"""Formatação de valores para mensagens ao cliente."""


def brl(cents: int) -> str:
    """7490 -> 'R$ 74,90'; 123456 -> 'R$ 1.234,56'."""
    reais, centavos = divmod(int(cents), 100)
    return f"R$ {reais:,}".replace(",", ".") + f",{centavos:02d}"
