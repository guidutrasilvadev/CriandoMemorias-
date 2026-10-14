"""Catálogo (filtros iguais aos do site) e carrinho (visitante, logado, mesclagem, desconto)."""
from tests.conftest import add_to_cart, bearer, register

ADMIN = {"X-Admin-Key": "admin-teste"}


# ---------- catálogo ----------
def test_list_and_pagination(client):
    r = client.get("/products", params={"page_size": 10, "page": 2}).json()
    assert r["total"] == 37 and len(r["items"]) == 10 and r["page"] == 2
    one = client.get("/products", params={"page_size": 100}).json()["items"][0]
    assert set(one) >= {"id", "slug", "name", "type", "type_label", "type_group", "occasion", "theme", "price_cents",
                        "featured", "demo"}
    assert one["demo"] is True and one["name"] == "Festa Abelhinha" and one["price_cents"] == 7490


def test_filters(client):
    by_occ = client.get("/products", params={"occasion": "Chá de bebê"}).json()
    assert by_occ["total"] == 1 and by_occ["items"][0]["name"] == "Chá de Bebê Anunciação"
    two = client.get("/products", params=[("occasion", "Chá de bebê"), ("occasion", "Festa adulto")]).json()
    assert two["total"] == 2
    assert client.get("/products", params={"type_group": "Moldes e arquivos"}).json()["total"] == 2
    assert client.get("/products", params={"theme": "Bichinhos"}).json()["total"] == 7
    cheap = client.get("/products", params={"max_price_cents": 3000}).json()
    assert cheap["total"] > 0 and all(p["price_cents"] <= 3000 for p in cheap["items"])
    both = client.get("/products", params={"min_price_cents": 6000, "max_price_cents": 7000}).json()
    assert both["total"] > 0 and all(6000 <= p["price_cents"] <= 7000 for p in both["items"])
    assert client.get("/products", params={"featured": "true"}).json()["total"] == 5


def test_search_ignores_accents_and_case(client):
    assert client.get("/products", params={"q": "cha de bebe"}).json()["total"] >= 1
    assert client.get("/products", params={"q": "ABELHINHA"}).json()["items"][0]["slug"] == "festa-abelhinha"
    assert client.get("/products", params={"q": "festa gatinhos"}).json()["total"] == 1
    assert client.get("/products", params={"q": "xyzxyz"}).json()["total"] == 0


def test_sort(client):
    asc = [p["price_cents"] for p in client.get("/products", params={"sort": "price_asc", "page_size": 100}).json()["items"]]
    assert asc == sorted(asc)
    desc = [p["price_cents"] for p in client.get("/products", params={"sort": "price_desc", "page_size": 100}).json()["items"]]
    assert desc == sorted(desc, reverse=True)
    names = [p["name"] for p in client.get("/products", params={"sort": "name_asc", "page_size": 100}).json()["items"]]
    assert names == sorted(names)
    assert client.get("/products", params={"sort": "invalido"}).status_code == 422


def test_facets_and_detail(client):
    f = client.get("/products/facets").json()
    assert f["total"] == 37 and f["price_min_cents"] == 2990 and f["price_max_cents"] == 7490
    assert {x["value"]: x["count"] for x in f["occasions"]}["Festa infantil"] == 29
    assert {x["value"]: x["count"] for x in f["type_groups"]}["Moldes e arquivos"] == 2
    assert client.get("/products/festa-margarida").json()["id"] == 2
    assert client.get("/products/2").json()["slug"] == "festa-margarida"
    assert client.get("/products/nao-existe").json()["error"]["code"] == "product_not_found"
    assert client.get("/products/9999").status_code == 404


def test_inactive_product_is_hidden(client):
    assert client.delete("/admin/products/1", headers=ADMIN).status_code == 204
    assert client.get("/products/1").status_code == 404
    assert client.get("/products").json()["total"] == 36
    assert client.get("/products", params={"q": "abelhinha"}).json()["total"] == 0


# ---------- carrinho de visitante ----------
def test_guest_cart(client):
    empty = client.get("/cart").json()
    assert empty["cart_id"] is None and empty["items"] == [] and empty["total_cents"] == 0

    r = client.post("/cart/items", json={"product_id": 1})
    assert r.status_code == 200
    cart_id = r.headers["X-Cart-Id"]
    h = {"X-Cart-Id": cart_id}
    assert r.json()["cart_id"] == cart_id and r.json()["subtotal_cents"] == 7490

    add_to_cart(client, 2, h)
    add_to_cart(client, 2, h)  # repetir não duplica (kit digital)
    cart = client.get("/cart", headers=h).json()
    assert cart["items_count"] == 2 and cart["subtotal_cents"] == 7490 * 2
    # visitante vê o desconto como convite ao login, sem abatê-lo
    d = cart["first_purchase_discount"]
    assert d["status"] == "login_required" and d["percent"] == 10 and d["estimated_amount_cents"] == 1498
    assert cart["discount_cents"] == 0 and cart["total_cents"] == 14980
    assert cart["installment_options"][0]["installments"] == 1

    after = client.delete("/cart/items/1", headers=h).json()
    assert after["items_count"] == 1 and after["items"][0]["product"]["id"] == 2
    assert client.delete("/cart", headers=h).json()["items_count"] == 0


def test_cart_unknown_product_and_foreign_header(client):
    assert client.post("/cart/items", json={"product_id": 999}).json()["error"]["code"] == "product_not_found"
    assert client.post("/cart/items", json={"product_id": 0}).status_code == 422
    # um id de carrinho inventado não dá acesso a nada
    assert client.get("/cart", headers={"X-Cart-Id": "00000000-0000-0000-0000-000000000000"}).json()["cart_id"] is None


def test_logged_cart_shows_discount_and_discounted_installments(client):
    t = register(client)
    h = bearer(t)
    r = client.post("/cart/items", json={"product_id": 1}, headers=h).json()
    d = r["first_purchase_discount"]
    assert d["status"] == "eligible" and r["discount_cents"] == 749 and r["total_cents"] == 7490 - 749
    assert r["installment_options"][0]["total_cents"] == 6741  # parcelas calculadas sobre o total com desconto
    assert "X-Cart-Id" not in client.get("/cart", headers=h).headers  # logado: carrinho preso à conta


def test_guest_cart_merges_on_login(client):
    r = client.post("/cart/items", json={"product_id": 1})
    h = {"X-Cart-Id": r.headers["X-Cart-Id"]}
    add_to_cart(client, 3, h)
    t = register(client)
    # a conta já tinha um kit no carrinho (outro dispositivo)
    add_to_cart(client, 3, bearer(t))
    add_to_cart(client, 4, bearer(t))
    merged = client.get("/cart", headers={**bearer(t), **h}).json()
    assert sorted(i["product"]["id"] for i in merged["items"]) == [1, 3, 4]
    # o carrinho de visitante deixou de existir; a conta continua com tudo
    assert client.get("/cart", headers=h).json()["cart_id"] is None
    assert client.get("/cart", headers=bearer(t)).json()["items_count"] == 3


def test_cart_of_another_user_is_not_reachable_by_header(client):
    a = register(client, "a@exemplo.com", "Ana Alves")
    add_to_cart(client, 1, bearer(a))
    cart_id = client.get("/cart", headers=bearer(a)).json()["cart_id"]
    # visitante com o id do carrinho de uma conta: nada
    assert client.get("/cart", headers={"X-Cart-Id": cart_id}).json()["items"] == []
    b = register(client, "b@exemplo.com", "Bia Barros")
    assert client.get("/cart", headers={**bearer(b), "X-Cart-Id": cart_id}).json()["items"] == []


def test_inactive_product_in_cart_is_reported(client):
    r = client.post("/cart/items", json={"product_id": 1})
    h = {"X-Cart-Id": r.headers["X-Cart-Id"]}
    add_to_cart(client, 2, h)
    client.delete("/admin/products/1", headers=ADMIN)
    cart = client.get("/cart", headers=h).json()
    assert cart["unavailable_product_ids"] == [1] and cart["items_count"] == 1 and cart["subtotal_cents"] == 7490


def test_discount_status_used_after_first_purchase(client):
    from tests.conftest import checkout
    t = register(client)
    add_to_cart(client, 1, bearer(t))
    order = checkout(client, t).json()
    client.post(f"/dev/orders/{order['id']}/approve")
    add_to_cart(client, 2, bearer(t))
    cart = client.get("/cart", headers=bearer(t)).json()
    assert cart["first_purchase_discount"]["status"] == "used" and cart["discount_cents"] == 0
