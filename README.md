# Criando Memórias: site e loja de kits digitais

Site estático (HTML, CSS e JavaScript puros, sem build) com catálogo, carrinho, login e pagamento (Pix, boleto e cartão parcelado), mais a API da loja em Python.

> **O catálogo é de demonstração.** Nomes, preços e capas são provisórios, só para montar o layout. Mantenha o repositório **privado** até entrarem os produtos reais da Criando Memórias.

## Estrutura

```
site/                 o site (index.html, assets/css, assets/js, assets/img, assets/video, assets/fonts)
backend/              a API da loja (FastAPI + SQLAlchemy): app/, tests/, seed/, scripts/
Iniciar loja.command  dois cliques no macOS: sobe a loja e abre no navegador
```

Cada pasta tem o seu README com os detalhes: [`site/README.md`](site/README.md) e [`backend/README.md`](backend/README.md).

## Rodar no seu computador

**Loja completa (API + site).** No macOS, dois cliques em `Iniciar loja.command`. Em qualquer sistema:

```
cd backend
./dev.sh
```

Na primeira vez ele cria o ambiente Python e instala tudo. Depois abra http://localhost:8100. O pagamento é **simulado**: ninguém é cobrado. A documentação interativa da API fica em http://localhost:8100/docs.

**Só o catálogo.** Abra `site/index.html` no navegador. O carrinho e o login precisam da API ligada.

## Testes

```
cd backend
.venv.nosync/bin/pytest -q
```

(depois de rodar `./dev.sh` uma vez, que cria o ambiente).

## Publicar

- **O site** é estático e funciona em qualquer hospedagem de arquivos (GitHub Pages, Netlify, Vercel). O `index.html` está dentro de `site/`, então aponte a hospedagem para essa pasta. Sem a API no ar, o catálogo aparece, mas o carrinho e o login não funcionam. Para uma prévia só de catálogo, ponha `loja: { ativa: false }` em `site/assets/js/config.js`.
- **A API** precisa de um servidor Python e de um banco (SQLite em teste, PostgreSQL em produção). Veja "Antes de ir ao ar" em [`backend/README.md`](backend/README.md).
- Em produção, ajuste `api` em `site/assets/js/config.js` para o endereço público da API.

## Antes de colocar no ar

- Trocar o catálogo de demonstração pelos kits reais (`site/assets/js/products.js` e o cadastro de kits da API).
- Definir o número de WhatsApp em `site/assets/js/config.js` (`whatsapp`).
- Conta na operadora de pagamento (a API vem com Mercado Pago, ainda não testado no ambiente de testes deles) e as credenciais no `.env`.
- Confirmar as regras provisórias: desconto de primeira compra (10%) e parcelamento (até 6x sem juros). Estão em `backend/.env.example`.
- Em produção: `ENV=production`, `SECRET_KEY`, `CORS_ORIGINS` e banco PostgreSQL.
- Pedir à cliente o vídeo de abertura em 3840 px nativos (o atual, em 4K, foi ampliado de uma resolução menor).

## O que não está neste repositório

O `.env` (segredos), o ambiente Python (`.venv.nosync`), o banco local (`data.nosync`) e os arquivos originais da marca (logos em alta e o vídeo 4K original) ficam fora, de propósito.
