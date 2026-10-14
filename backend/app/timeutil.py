"""Datas: tudo é guardado em UTC, sem fuso (naive), e sai da API com "Z" no final."""
from datetime import datetime, timezone


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)
