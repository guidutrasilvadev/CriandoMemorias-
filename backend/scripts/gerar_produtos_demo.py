"""Gera seed/produtos_demo.json a partir do catálogo provisório do site (site/assets/js/products.js).
Uso (na pasta backend):  python3 scripts/gerar_produtos_demo.py
Só é preciso rodar de novo se o catálogo de demonstração do site mudar."""
import json
import re
import unicodedata
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
SRC = BACKEND.parent / "site" / "assets" / "js" / "products.js"
OUT = BACKEND / "seed" / "produtos_demo.json"


def slugify(text: str) -> str:
    plain = "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", "-", plain.lower()).strip("-")


def main() -> None:
    js = SRC.read_text(encoding="utf-8")
    consts = dict(re.findall(r'(\b[A-Z]{3})\s*=\s*"([^"]+)"', js))
    row = re.compile(r'\[\s*"(?P<name>[^"]+)"\s*,\s*"(?P<type>\w+)"\s*,\s*(?P<oc>[A-Z]{3})\s*,\s*(?P<theme>[A-Z]{3})\s*,'
                     r'\s*(?P<price>[\d.]+)\s*,\s*"\w+"\s*,\s*\[[^\]]*\]\s*,\s*(?P<feat>[01])\s*\]')
    products = []
    for i, m in enumerate(row.finditer(js), start=1):
        products.append({"id": i, "slug": slugify(m["name"]), "name": m["name"], "type": m["type"],
                         "occasion": consts[m["oc"]], "theme": consts[m["theme"]],
                         "price_cents": int(round(float(m["price"]) * 100)), "featured": m["feat"] == "1"})
    slugs = [p["slug"] for p in products]
    assert len(products) and len(set(slugs)) == len(slugs), "catálogo vazio ou com slugs repetidos"
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(products, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{len(products)} kits gravados em {OUT}")


if __name__ == "__main__":
    main()
