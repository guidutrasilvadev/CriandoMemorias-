"""Carga inicial do catálogo de DEMONSTRAÇÃO (os mesmos 37 kits provisórios do site).
Eles ficam marcados como `demo` e não podem ser comprados em produção. Troque pelo catálogo real
pelo painel administrativo (POST /admin/products/import)."""
import json
import logging

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from .config import BACKEND_DIR
from .models import Product
from .services.catalog import search_text

log = logging.getLogger("cm.seed")
SEED_FILE = BACKEND_DIR / "seed" / "produtos_demo.json"


def seed_demo_products(db: Session) -> int:
    """Insere o catálogo de demonstração se a tabela de produtos estiver vazia. Devolve quantos inseriu."""
    if db.scalar(select(func.count(Product.id))):
        return 0
    rows = json.loads(SEED_FILE.read_text(encoding="utf-8"))
    for r in rows:
        db.add(Product(id=r["id"], slug=r["slug"], name=r["name"], type=r["type"], occasion=r["occasion"],
                       theme=r["theme"], price_cents=r["price_cents"], featured=r["featured"], active=True, demo=True,
                       search_text=search_text(r["name"], r["theme"], r["occasion"], r["type"])))
    db.commit()
    if db.get_bind().dialect.name == "postgresql":  # ids foram inseridos à mão: realinha a sequência
        db.execute(text("SELECT setval(pg_get_serial_sequence('products','id'), (SELECT MAX(id) FROM products))"))
        db.commit()
    log.info("catálogo de demonstração carregado: %d kits", len(rows))
    return len(rows)
