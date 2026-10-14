"""Catálogo: listagem com filtros (os mesmos do site), facetas e utilitários de cadastro."""
import re
import unicodedata
from typing import Dict, List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..errors import bad_request
from ..models import Product
from ..schemas import FacetCount, FacetsOut, ProductOut

# tipo -> (rótulo, grupo). Mesmos valores do TIPOS em site/assets/js/products.js.
TYPES: Dict[str, Tuple[str, str]] = {
    "kit": ("Kit digital", "Kits digitais"),
    "mesa": ("Kit para mesa posta", "Mesa posta e cestas"),
    "cesta": ("Kit para cesta", "Mesa posta e cestas"),
    "mesacesta": ("Kit para cesta ou mesa posta", "Mesa posta e cestas"),
    "molde": ("Arquivo digital de molde", "Moldes e arquivos"),
    "arquivo": ("Arquivo digital", "Moldes e arquivos"),
}

SORTS = {
    "featured": (Product.featured.desc(), Product.id.asc()),
    "price_asc": (Product.price_cents.asc(), Product.name.asc()),
    "price_desc": (Product.price_cents.desc(), Product.name.asc()),
    "name_asc": (Product.name.asc(),),
    "name_desc": (Product.name.desc(),),
}


def strip_accents(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", strip_accents(text).lower()).strip("-")


def search_text(name: str, theme: str, occasion: str, type_key: str) -> str:
    label = TYPES.get(type_key, (type_key, ""))[0]
    return strip_accents(f"{name} {theme} {occasion} {label}").lower()


def product_out(p: Product) -> ProductOut:
    label, group = TYPES.get(p.type, (p.type, p.type))
    return ProductOut(id=p.id, slug=p.slug, name=p.name, type=p.type, type_label=label, type_group=group,
                      occasion=p.occasion, theme=p.theme, price_cents=p.price_cents, featured=p.featured, demo=p.demo)


def check_type(type_key: str) -> None:
    if type_key not in TYPES:
        raise bad_request(f"Tipo inválido. Use um destes: {', '.join(TYPES)}.", "invalid_type")


def list_products(db: Session, *, q: Optional[str], occasions: List[str], type_groups: List[str], themes: List[str],
                  min_price: Optional[int], max_price: Optional[int], featured: Optional[bool], sort: str,
                  page: int, page_size: int) -> Tuple[List[Product], int]:
    stmt = select(Product).where(Product.active.is_(True))
    if q:
        for token in strip_accents(q).lower().split():
            stmt = stmt.where(Product.search_text.contains(token, autoescape=True))
    if occasions:
        stmt = stmt.where(Product.occasion.in_(occasions))
    if type_groups:
        keys = [k for k, (_, g) in TYPES.items() if g in type_groups]
        stmt = stmt.where(Product.type.in_(keys or ["__nenhum__"]))
    if themes:
        stmt = stmt.where(Product.theme.in_(themes))
    if min_price is not None:
        stmt = stmt.where(Product.price_cents >= min_price)
    if max_price is not None:
        stmt = stmt.where(Product.price_cents <= max_price)
    if featured is not None:
        stmt = stmt.where(Product.featured.is_(featured))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    stmt = stmt.order_by(*SORTS.get(sort, SORTS["featured"])).offset((page - 1) * page_size).limit(page_size)
    return list(db.scalars(stmt)), total


def facets(db: Session) -> FacetsOut:
    active = Product.active.is_(True)

    def counts(col):
        return list(db.execute(select(col, func.count()).where(active).group_by(col).order_by(func.count().desc())))

    occasions = [FacetCount(value=v, label=v, count=c) for v, c in counts(Product.occasion)]
    themes = [FacetCount(value=v, label=v, count=c) for v, c in counts(Product.theme)]
    groups: Dict[str, int] = {}
    for key, c in counts(Product.type):
        g = TYPES.get(key, (key, key))[1]
        groups[g] = groups.get(g, 0) + c
    type_groups = [FacetCount(value=g, label=g, count=c) for g, c in sorted(groups.items(), key=lambda x: -x[1])]
    lo, hi, total = db.execute(select(func.min(Product.price_cents), func.max(Product.price_cents),
                                      func.count()).where(active)).one()
    return FacetsOut(occasions=occasions, type_groups=type_groups, themes=themes,
                     price_min_cents=lo or 0, price_max_cents=hi or 0, total=total or 0)


def find_product(db: Session, ref: str, *, include_inactive: bool = False) -> Optional[Product]:
    stmt = select(Product).where(Product.id == int(ref)) if ref.isdigit() else select(Product).where(Product.slug == ref)
    p = db.scalar(stmt)
    if p is not None and not p.active and not include_inactive:
        return None
    return p
