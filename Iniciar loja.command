#!/usr/bin/env bash
# Dois cliques (macOS): sobe a loja (API + site) e abre no navegador. Na primeira vez instala o que precisa, o que leva um minuto.
cd "$(dirname "$0")/backend" || exit 1
PORT="${PORT:-8100}"
( for _ in $(seq 1 180); do curl -fs "http://localhost:$PORT/health" >/dev/null 2>&1 && { open "http://localhost:$PORT"; exit 0; }; sleep 1; done ) &
./dev.sh
