#!/usr/bin/env bash
# Sobe a loja em modo desenvolvimento: a API e o site (../site) em http://localhost:8100, documentação da API em /docs.
# Na primeira vez cria o ambiente Python em .venv.nosync (o iCloud não sincroniza pastas .nosync) e instala tudo.
set -euo pipefail
cd "$(dirname "$0")"
VENV=".venv.nosync"
if [ ! -x "$VENV/bin/uvicorn" ]; then
  echo "Criando o ambiente Python (só na primeira vez)..."
  python3 -m venv "$VENV"
  "$VENV/bin/pip" install -q --upgrade pip
  "$VENV/bin/pip" install -q -r requirements-dev.txt
fi
[ -f .env ] || cp .env.example .env
echo "Loja no ar:  http://localhost:${PORT:-8100}   ·   documentação da API:  http://localhost:${PORT:-8100}/docs   ·   Ctrl+C para parar"
exec "$VENV/bin/uvicorn" app.main:create_app --factory --reload --port "${PORT:-8100}"
