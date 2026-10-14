"""Aplicação FastAPI. Suba com:  uvicorn app.main:create_app --factory --port 8100"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from .config import BACKEND_DIR, get_settings, load_dotenv
from .db import get_sessionmaker, init_db
from .errors import ApiError
from .routers import admin, auth, cart, catalog, dev, me, meta, shop
from .seed import seed_demo_products

log = logging.getLogger("cm.app")

DESCRIPTION = """
API da loja de kits digitais da **Criando Memórias**: catálogo, carrinho, compra (Pix, boleto e cartão parcelado)
e login (Google, Facebook, e-mail ou telefone).

* Valores sempre em **centavos** (`price_cents`).
* Erros vêm como `{"error": {"code", "message", "fields"?}}`. Use `code` na lógica da tela; `message` já está em português.
* Rotas privadas pedem `Authorization: Bearer <access_token>`.
* Carrinho de visitante: guarde o `cart_id` e envie em `X-Cart-Id`.
"""

PRIVATE_PREFIXES = ("/auth", "/cart", "/checkout", "/orders", "/me", "/admin", "/dev", "/payments")
MAX_BODY_BYTES = 1_000_000


def create_app(load_env: bool = True) -> FastAPI:
    if load_env:
        load_dotenv()
    s = get_settings()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    # o httpx registra a URL de cada chamada externa; nas do Facebook o token e o segredo do app vão na URL
    for noisy in ("httpx", "httpcore"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        init_db()
        if s.auto_seed_demo:
            with get_sessionmaker()() as db:
                seed_demo_products(db)
        yield

    app = FastAPI(title="Criando Memórias — API da loja", version="1.0.0", description=DESCRIPTION, lifespan=lifespan,
                  docs_url=None if s.is_production else "/docs", redoc_url=None,
                  openapi_url=None if s.is_production else "/openapi.json")

    app.add_middleware(CORSMiddleware, allow_origins=s.cors_origins, allow_credentials=False,
                       allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
                       allow_headers=["Authorization", "Content-Type", "X-Cart-Id", "Idempotency-Key", "X-Admin-Key"],
                       expose_headers=["X-Cart-Id", "Retry-After"], max_age=600)

    @app.middleware("http")
    async def safety(request: Request, call_next):
        length = request.headers.get("content-length")
        if length and length.isdigit() and int(length) > MAX_BODY_BYTES:
            return JSONResponse({"error": {"code": "payload_too_large", "message": "Requisição grande demais."}}, 413)
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        if request.url.path.startswith(PRIVATE_PREFIXES):
            response.headers["Cache-Control"] = "no-store"
        if s.is_production:
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        return response

    @app.exception_handler(ApiError)
    async def api_error(_: Request, exc: ApiError):
        return JSONResponse(exc.body(), status_code=exc.status, headers=exc.headers)

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, exc: RequestValidationError):
        fields = {}
        for e in exc.errors():
            loc = [str(p) for p in e["loc"] if p not in ("body", "query", "path", "header")]
            fields[".".join(loc) or "corpo"] = str(e["msg"]).replace("Value error, ", "")
        return JSONResponse({"error": {"code": "validation_error", "message": "Confira os campos informados.",
                                       "fields": fields}}, status_code=422)

    @app.exception_handler(StarletteHTTPException)
    async def http_error(_: Request, exc: StarletteHTTPException):
        messages = {404: ("not_found", "Rota não encontrada."), 405: ("method_not_allowed", "Método não permitido.")}
        code, message = messages.get(exc.status_code, (f"http_{exc.status_code}", "Não foi possível concluir."))
        return JSONResponse({"error": {"code": code, "message": message}}, status_code=exc.status_code)

    @app.exception_handler(Exception)
    async def unexpected(_: Request, exc: Exception):
        log.exception("erro inesperado")
        return JSONResponse({"error": {"code": "internal_error", "message": "Algo deu errado. Tente de novo."}},
                            status_code=500)

    for module in (meta, auth, catalog, cart, shop, me, admin, dev):
        app.include_router(module.router)

    # Em desenvolvimento a API também entrega o site (../site): abra http://localhost:8100 e tudo roda na mesma origem,
    # sem CORS. Montado por último para nunca encobrir uma rota da API. Em produção o site tem hospedagem própria.
    site_dir = BACKEND_DIR.parent / "site"
    if s.serve_site and (site_dir / "index.html").is_file():
        app.mount("/", StaticFiles(directory=str(site_dir), html=True), name="site")
    return app
