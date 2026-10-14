"""Administração (cabeçalho X-Admin-Key): cadastro de kits e acompanhamento de pedidos.
Serve até existir um painel; guarde a ADMIN_API_KEY como uma senha."""
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import Settings, get_settings
from ..db import get_db
from ..deps import require_admin
from ..errors import conflict, not_found
from ..gateways import get_gateway
from ..gateways.base import PaymentGateway
from ..models import Order, Product
from ..schemas import OrderOut, ProductIn, ProductOut, ProductPatch
from ..services import catalog, orders

router = APIRouter(prefix="/admin", tags=["Administração"], dependencies=[Depends(require_admin)])


class ProductAdminOut(ProductOut):
    active: bool
    file_key: Optional[str]


class AdminOrderOut(OrderOut):
    user_id: str
    payer_name: str
    payer_email: str
    payer_cpf_masked: str


def _product_admin(p: Product) -> ProductAdminOut:
    return ProductAdminOut(**catalog.product_out(p).model_dump(), active=p.active, file_key=p.file_key)


def _order_admin(o: Order) -> AdminOrderOut:
    return AdminOrderOut(**orders.order_out(o).model_dump(), user_id=o.user_id, payer_name=o.payer_name,
                         payer_email=o.payer_email, payer_cpf_masked=o.payer_cpf_masked)


def _apply(p: Product, data: dict) -> None:
    for key, value in data.items():
        setattr(p, key, value)
    p.search_text = catalog.search_text(p.name, p.theme, p.occasion, p.type)


@router.get("/products", response_model=List[ProductAdminOut], summary="Todos os kits (inclui inativos)")
def list_products(db: Session = Depends(get_db)):
    return [_product_admin(p) for p in db.scalars(select(Product).order_by(Product.id))]


@router.post("/products", response_model=ProductAdminOut, status_code=201, summary="Cadastrar um kit")
def create_product(body: ProductIn, db: Session = Depends(get_db)):
    catalog.check_type(body.type)
    slug = body.slug or catalog.slugify(body.name)
    if db.scalar(select(Product.id).where(Product.slug == slug)):
        raise conflict("Já existe um kit com este slug.", "slug_in_use")
    p = Product(slug=slug)
    if body.id is not None:
        p.id = body.id
    _apply(p, body.model_dump(exclude={"slug", "id"}))
    db.add(p)
    db.commit()
    return _product_admin(p)


@router.post("/products/import", response_model=List[ProductAdminOut],
             summary="Importar vários kits de uma vez (atualiza quem já existe pelo id ou pelo slug)")
def import_products(body: List[ProductIn], db: Session = Depends(get_db)):
    out = []
    for row in body:
        catalog.check_type(row.type)
        slug = row.slug or catalog.slugify(row.name)
        p = db.get(Product, row.id) if row.id is not None else None
        if p is None:
            p = db.scalar(select(Product).where(Product.slug == slug))
        if p is None:
            p = Product(slug=slug)
            if row.id is not None:
                p.id = row.id
            db.add(p)
        else:
            p.slug = slug
        _apply(p, row.model_dump(exclude={"slug", "id"}))
        out.append(p)
    db.commit()
    return [_product_admin(p) for p in out]


@router.patch("/products/{product_id}", response_model=ProductAdminOut, summary="Alterar um kit")
def patch_product(product_id: int, body: ProductPatch, db: Session = Depends(get_db)):
    p = db.get(Product, product_id)
    if p is None:
        raise not_found("Kit não encontrado.", "product_not_found")
    data = body.model_dump(exclude_unset=True)
    if "type" in data:
        catalog.check_type(data["type"])
    _apply(p, data)
    db.commit()
    return _product_admin(p)


@router.delete("/products/{product_id}", status_code=204, summary="Tirar um kit do ar (desativa; pedidos antigos continuam)")
def deactivate_product(product_id: int, db: Session = Depends(get_db)):
    p = db.get(Product, product_id)
    if p is None:
        raise not_found("Kit não encontrado.", "product_not_found")
    p.active = False
    db.commit()


@router.get("/orders", response_model=List[AdminOrderOut], summary="Pedidos (mais recentes primeiro)")
def list_orders(status: Optional[str] = Query(None, pattern="^(pending|paid|failed|expired|canceled|refunded)$"),
                limit: int = Query(50, ge=1, le=200), db: Session = Depends(get_db)):
    stmt = select(Order).order_by(Order.created_at.desc()).limit(limit)
    if status:
        stmt = stmt.where(Order.status == status)
    return [_order_admin(o) for o in db.scalars(stmt)]


@router.post("/orders/{order_id}/reconcile", response_model=AdminOrderOut,
             summary="Consultar a operadora e atualizar o pedido agora")
def reconcile(order_id: str, db: Session = Depends(get_db), s: Settings = Depends(get_settings),
              gateway: PaymentGateway = Depends(get_gateway)):
    order = db.get(Order, order_id)
    if order is None:
        raise not_found("Pedido não encontrado.", "order_not_found")
    return _order_admin(orders.refresh_order(db, s, gateway, order, min_interval=0))
