"""Catálogo público: lista com os mesmos filtros do site, detalhe e contagens para os filtros."""
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..db import get_db
from ..errors import not_found
from ..schemas import FacetsOut, ProductOut, ProductPage
from ..services import catalog

router = APIRouter(prefix="/products", tags=["Catálogo"])


@router.get("", response_model=ProductPage, summary="Listar kits")
def list_products(
        q: Optional[str] = Query(None, max_length=80, description="Busca por nome, tema, ocasião ou tipo (sem acento)"),
        occasion: List[str] = Query([], description="Ocasião; repita o parâmetro para mais de uma"),
        type_group: List[str] = Query([], description="Grupo do tipo (ex.: 'Kits digitais')"),
        theme: List[str] = Query([], description="Tema"),
        min_price_cents: Optional[int] = Query(None, ge=0),
        max_price_cents: Optional[int] = Query(None, ge=0),
        featured: Optional[bool] = None,
        sort: Literal["featured", "price_asc", "price_desc", "name_asc", "name_desc"] = "featured",
        page: int = Query(1, ge=1),
        page_size: int = Query(50, ge=1, le=100),
        db: Session = Depends(get_db)):
    items, total = catalog.list_products(db, q=q, occasions=occasion, type_groups=type_group, themes=theme,
                                         min_price=min_price_cents, max_price=max_price_cents, featured=featured,
                                         sort=sort, page=page, page_size=page_size)
    return ProductPage(items=[catalog.product_out(p) for p in items], total=total, page=page, page_size=page_size)


@router.get("/facets", response_model=FacetsOut, summary="Contagens por ocasião, tipo e tema (para montar os filtros)")
def facets(db: Session = Depends(get_db)):
    return catalog.facets(db)


@router.get("/{ref}", response_model=ProductOut, summary="Detalhe de um kit (por id ou slug)")
def detail(ref: str, db: Session = Depends(get_db)):
    p = catalog.find_product(db, ref)
    if p is None:
        raise not_found("Kit não encontrado.", "product_not_found")
    return catalog.product_out(p)
