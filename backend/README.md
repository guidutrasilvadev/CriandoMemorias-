# Backend da loja — Criando Memórias

API da loja de kits digitais: catálogo, carrinho, compra com **Pix, boleto e cartão parcelado**, e login com **Google, Facebook, e-mail ou telefone**. As telas que usam esta API (carrinho, entrar com os benefícios, pagamento, minha conta) já estão no site, em `../site/` (veja `../site/README.md`).

Python + FastAPI + SQLAlchemy. Tem documentação interativa de todas as rotas em **http://localhost:8100/docs** (rode e abra: dá para testar cada chamada ali).

## O que está pronto

| Área | O que faz |
|---|---|
| Catálogo | Lista com os mesmos filtros do site (ocasião, tipo, tema, preço, busca sem acento, ordem, páginas) e contagens para montar os filtros |
| Carrinho | Visitante ou logado; carrinho do visitante é mesclado ao entrar; mostra desconto e parcelas |
| Compra | Pix (copia e cola + QR), boleto (linha digitável + PDF), cartão em até N vezes; acompanhamento do pedido; cancelamento; expiração |
| Desconto | Primeira compra paga: percentual configurável, uma vez por pessoa (conta **e** CPF) |
| Login | E-mail/telefone + senha, código por e-mail/SMS/WhatsApp, Google, Facebook; sessão curta + renovação; vincular logins |
| Tela de login | `GET /auth/benefits` devolve os benefícios (incluindo o desconto) já em português, prontos para exibir |
| Pós-compra | Pedidos, “meus kits” (`/me/library`), reembolso tirando o kit da biblioteca |
| Administração | Cadastro/importação de kits e acompanhamento de pedidos, por chave (`X-Admin-Key`) |
| Simulador | Gateway de mentira para testar tudo sem conta em operadora; a tela de pagamento mostra botões para simular aprovado, recusado e expirado |

**Mais de 140 testes automatizados** cobrem login, carrinho, desconto, parcelas, Pix, boleto, cartão, webhooks, expiração, reembolso, administração e segurança. O adaptador do Mercado Pago é testado com respostas simuladas; **ainda não foi testado no sandbox real** (veja “Antes de ir ao ar”).

## Rodando

```
cd backend
./dev.sh
```

Na primeira vez cria o ambiente Python em `.venv.nosync` (o iCloud não sincroniza essa pasta) e copia `.env.example` para `.env`. Depois sobe em http://localhost:8100 com o catálogo de demonstração carregado. Testes: `.venv.nosync/bin/python -m pytest`.

Em desenvolvimento a própria API **entrega o site** (a pasta `../site`): abra **http://localhost:8100** e a loja inteira funciona, sem CORS. Também dá para dar dois cliques em `../Iniciar loja.command` (sobe tudo e abre o navegador). O site aberto direto do arquivo (`file://`) também funciona com a API ligada: o CORS de desenvolvimento aceita esse caso. Com `SERVE_SITE=false` a API não entrega o site (em produção é assim: o site fica na hospedagem dele).

### Testando pagamentos sem operadora (simulador)

Com `PAYMENT_GATEWAY=simulated` (padrão em dev):

* **Cartão:** envie `card_token` = `tok_approved` (aprova na hora), `tok_rejected` (recusa) ou `tok_pending` (fica em análise). Use qualquer `card_brand`, por exemplo `visa`.
* **Pix e boleto:** o pedido fica pendente. Para “o cliente pagou”: `POST /dev/orders/{id}/approve` (também `reject` e `expire`). Essa rota só existe em desenvolvimento.
* Os códigos de Pix e boleto gerados são falsos e não funcionam em aplicativo de banco.

## Como as telas usam a API

Este guia descreve o que cada tela chama. As telas do site já fazem isso (arquivos em `../site/assets/js/`: `api.js`, `loja.js`, `entrar.js`, `conta.js`, `checkout.js`); use o guia para ajustar uma tela ou para fazer outro cliente (aplicativo, outro site).

Valores sempre em **centavos** (`7490` = R$ 74,90). Erros sempre assim, com `code` estável para a lógica e `message` já em português (`fields` aponta o campo com problema; `details` traz dados extras, como o novo total em `price_changed`):

```json
{"error": {"code": "cart_empty", "message": "Seu carrinho está vazio.", "fields": {"payer.cpf": "CPF inválido."}}}
```

Rotas privadas pedem `Authorization: Bearer <access_token>`.

### 1. Tela de login
1. `GET /auth/benefits` → `headline`, `benefits[]` (título e descrição), `providers[]` (quais botões mostrar: `google`, `facebook`, `email`, `phone`) e `fine_print`. Com o desconto desligado ele some sozinho da lista.
2. Entrar (todas devolvem o mesmo `TokenOut`: `access_token`, `refresh_token`, `expires_in`, `user`, `is_new_user`, `first_purchase_discount`):
   * **E-mail/telefone + senha:** `POST /auth/register` (cria) e `POST /auth/login` (`identifier` aceita e-mail ou telefone).
   * **Código (sem senha):** `POST /auth/otp/request` (`channel`: `email`, `sms` ou `whatsapp`) e depois `POST /auth/otp/verify`. Cria a conta se ainda não existir. Em desenvolvimento a resposta traz `dev_code`.
   * **Google:** botão do Google Identity Services; o `credential` que ele entrega vai em `POST /auth/google` `{"id_token": credential}`.
   * **Facebook:** `FB.login`; o `authResponse.accessToken` vai em `POST /auth/facebook` `{"access_token": ...}`.
3. Guarde `refresh_token` e `access_token`. Quando uma chamada voltar `401` com `token_expired`, chame `POST /auth/refresh` e repita. Cada refresh troca o token por um novo; **reaproveitar um refresh antigo derruba todas as sessões** (proteção contra roubo). Sair: `POST /auth/logout`.
4. Se o e-mail do Facebook já tem conta, volta `409 account_exists_link_required`: peça para a pessoa entrar de outro jeito e vincular em “Minha conta” (`POST /me/link/facebook`, `/me/link/google`). O Google, quando confirma o e-mail, vincula sozinho.

### 2. Carrinho
* Visitante: `POST /cart/items` `{"product_id": 2}`. A resposta traz `cart_id` e o cabeçalho `X-Cart-Id`; guarde e mande `X-Cart-Id` nas próximas chamadas (`GET /cart`, `DELETE /cart/items/2`, `DELETE /cart`).
* Ao entrar, mande o `X-Cart-Id` junto na primeira chamada autenticada: o carrinho do visitante é mesclado ao da conta. Depois disso descarte o id; logado, não precisa.
* O carrinho já devolve tudo que a tela precisa: `subtotal_cents`, `discount_cents`, `total_cents`, `installment_options[]` e `first_purchase_discount`:
  * `status: "login_required"` → mostre “Entre e ganhe X% (≈ R$ …)” usando `percent` e `estimated_amount_cents`;
  * `"eligible"` → o desconto já está abatido no total; `"used"` → sem desconto; `"disabled"` → nada a mostrar.
* Kits digitais não têm quantidade: adicionar o mesmo kit duas vezes não muda nada.

### 3. Pagamento — `POST /checkout` (exige login)
Corpo:

```json
{
  "payment_method": "pix | boleto | card",
  "installments": 3,
  "expected_total_cents": 6741,
  "card_token": "token gerado no navegador", "card_brand": "visa",
  "payer": {"name": "Ana Souza", "email": "ana@exemplo.com", "cpf": "529.982.247-25", "phone": "(11) 98765-4321",
            "address": {"zip_code": "01310-100", "street": "Av. Paulista", "number": "1000", "neighborhood": "Bela Vista", "city": "São Paulo", "state": "SP"}}
}
```

* Mande um cabeçalho **`Idempotency-Key` novo a cada tentativa de pagar** (um UUID gerado quando a pessoa clica em “pagar”); se a rede cair e você repetir a mesma chamada com a mesma chave, volta o mesmo pedido, sem cobrar duas vezes.
* `address` só é obrigatório no boleto. `installments` só vale no cartão (use as opções do carrinho).
* **Preço e desconto são calculados no servidor**; o que o navegador mandar sobre valores é ignorado, com uma exceção que protege quem paga: `expected_total_cents` é o total que a tela **mostrou** (no cartão parcelado, já com juros). Se o servidor chegar a outro valor (por exemplo, o desconto de primeira compra não vale para aquele CPF, que já o usou), **nada é cobrado** e volta `409 price_changed` com `error.details = {total_cents, charged_cents, discount_cents, discount_code}`: mostre o valor novo e deixe a pessoa pagar de novo. Se o campo for omitido, vale o valor do servidor.
* A resposta é o pedido (`OrderOut`). O que fazer por método:
  * **Pix:** mostre `payment.pix.qr_code` (texto “copia e cola”; gere o QR no navegador com uma biblioteca) e/ou `qr_code_base64` (PNG pronto, quando a operadora envia) com a contagem até `payment.pix.expires_at`. Consulte `GET /orders/{id}` a cada 3–5 s até `status` deixar de ser `pending`.
  * **Boleto:** mostre `payment.boleto.digitable_line`, o botão para `url` (PDF) e `due_date`. Explique que pode levar até 2 dias úteis para compensar; consulte `GET /orders/{id}` quando a pessoa voltar.
  * **Cartão:** a resposta já vem decidida: `status: "paid"` (aprovado), `"failed"` com `payment.status: "rejected"` (recusado; o carrinho continua, deixe tentar de novo) ou `"pending"` (em análise; acompanhe como no Pix).
* **Cartão: o backend nunca recebe o número do cartão.** A tela usa o SDK da operadora (MercadoPago.js) com a chave pública (`GET /config/public` → `card.public_key`) para gerar o `card_token` e descobrir a bandeira (`card_brand`).
* Estados do pedido: `pending` (aguardando), `paid`, `failed`, `expired`, `canceled`, `refunded`. Ao pagar, o carrinho esvazia sozinho. `POST /orders/{id}/cancel` cancela pedido pendente. Iniciar um novo checkout cancela o pedido pendente anterior.

### 4. Depois da compra
`GET /orders` (meus pedidos), `GET /orders/{id}`, `GET /me/library` (kits comprados) e `GET /me` / `PATCH /me`. A entrega dos arquivos para download **ainda não existe** (ver pendências); hoje `download_available` é sempre `false`.

### 5. Configurações para as telas
`GET /config/public`: formas de pagamento, regras de parcelamento, prazos de Pix e boleto, percentual do desconto, `google_client_id`, `facebook_app_id` e a chave pública do cartão. Parcelas de um valor qualquer: `GET /payments/installments?amount_cents=7490`.

## Decisões que tomei (você pode mudar)

| Decisão | Por quê |
|---|---|
| **Compra exige login** | O desconto de primeira compra, o histórico de pedidos e a biblioteca de kits dependem de conta. O carrinho funciona sem login. |
| **Mercado Pago como primeira operadora real** | Cobre Pix, boleto e cartão parcelado e é a mais comum em loja pequena no Brasil. Fica isolada em `app/gateways/mercadopago.py`; trocar por Asaas, Pagar.me ou Stripe é escrever outra classe (veja `base.py`). |
| **Desconto de 10% (provisório)** | A cliente não definiu. Em `FIRST_PURCHASE_DISCOUNT_PERCENT`; `0` desliga e some da tela de login. Vale uma vez por pessoa: bloqueado por conta **e por CPF**. |
| **Até 6x sem juros, parcela mínima R$ 5,00 (provisório)** | Não inventei juros. Ajuste `MAX_INSTALLMENTS`, `INTEREST_FREE_INSTALLMENTS`, `MONTHLY_INTEREST_PERCENT` e `MIN_INSTALLMENT_CENTS` para **o mesmo que a operadora cobra**; quem cobra de verdade é ela. |
| **CPF completo não fica no banco** | Vai só para a operadora. Aqui ficam um hash (para o desconto não repetir) e a máscara `***.982.247-**`. Se a cliente precisar emitir nota fiscal, isso muda. |
| **Kits de demonstração não vendem em produção** | O catálogo atual tem nomes e preços de outra loja, só para montar o layout. Marcados `demo`, são bloqueados no checkout em produção. Troque pelo catálogo real em `POST /admin/products/import`. |
| **Pix 30 min, boleto 3 dias** | `PIX_EXPIRATION_MINUTES`, `BOLETO_DUE_DAYS`. Pagamento que chega depois do prazo ainda libera o kit (o dinheiro entrou). |
| **Valores em centavos, datas em UTC (`...Z`)** | Evita erro de arredondamento e de fuso. |

## Antes de ir ao ar

1. **Mercado Pago, no sandbox, nesta ordem:** Pix, boleto, cartão aprovado, cartão recusado, e o recebimento do webhook. O adaptador foi escrito pela documentação, sem credenciais para testar; se algum campo divergir, o ajuste está concentrado em `_payload`, `_parse` e `verify_webhook`. Credenciais, chave pública e a “assinatura secreta” do webhook ficam no painel de desenvolvedor deles.
2. **Endereço público e HTTPS.** O webhook precisa de `PUBLIC_API_URL` acessível pela internet (em desenvolvimento use um túnel, como ngrok). Cadastre `https://SUA-API/webhooks/mercadopago` no painel. Se um aviso chegar antes de o pedido ser gravado, a API responde 404 de propósito para a operadora tentar de novo; e `GET /orders/{id}` também reconcilia sozinho.
3. **Variáveis de produção** (`ENV=production` recusa subir se faltar algo): `SECRET_KEY` (32+ caracteres; **não troque depois** sem planejar, porque invalida sessões e o controle do desconto por CPF), `DATABASE_URL` (PostgreSQL: `pip install "psycopg[binary]"` e `postgresql+psycopg://...`), `CORS_ORIGINS` (o endereço do site), `PAYMENT_GATEWAY=mercadopago`, `MERCADOPAGO_*`, `ADMIN_API_KEY`, `TRUST_PROXY=true` se houver proxy/CDN. Suba com `uvicorn app.main:create_app --factory --host 0.0.0.0 --port $PORT`.
4. **Login social:** crie o ID do cliente OAuth no Google e o app no Facebook (com a permissão de e-mail) e preencha `GOOGLE_CLIENT_ID`, `FACEBOOK_APP_ID`, `FACEBOOK_APP_SECRET`. Sem isso o botão fica fora de `providers`.
5. **Código por SMS/WhatsApp/e-mail:** em produção é preciso configurar SMTP (e-mail) e/ou Twilio (SMS e WhatsApp); sem isso a API responde 503 nesses canais. O login por e-mail/telefone com senha funciona sem isso.
6. **Catálogo real:** importe os kits da cliente; `file_key` guarda o caminho do arquivo de cada kit.
7. **Backup do banco** e monitoramento dos logs (não registram dados de cartão, senha ou token).

## Segurança — o que já está feito

* Senhas com **Argon2id**; mensagens e tempo iguais para “senha errada” e “conta inexistente”.
* Sessão: JWT de 15 min + refresh token aleatório guardado só como hash, com rotação e detecção de reuso.
* Códigos de verificação: 6 dígitos guardados com HMAC, validade de 10 min, 5 tentativas, 60 s entre pedidos e no máximo 5 por dia por contato.
* Limite de tentativas por IP (e por conta no login) em `/auth/*` e no checkout.
* Cartão nunca passa pelo servidor (tokenização na operadora). Webhook com assinatura verificada **e** estado reconsultado na operadora, nunca confiando no corpo do aviso. Estados do pagamento só avançam.
* Pedido gravado **antes** de falar com a operadora; chave de idempotência na operadora; preço sempre do banco.
* Vínculo de login social sem tomar conta de ninguém: Google só vincula e-mail confirmado (e derruba a senha de um pré-cadastro com o mesmo e-mail); Facebook nunca vincula sozinho.
* CORS fechado por padrão em produção, cabeçalhos de segurança, `Cache-Control: no-store` em rotas privadas, corpo limitado a 1 MB, `/docs` desligado em produção, erros internos sem detalhes.

## O que ainda não existe (decisões ou trabalho pendente)

* **Entrega dos arquivos do kit.** A cliente ainda não definiu o formato (a página do kit diz “a confirmar”). O que há: pedido pago, `/me/library` e `file_key` por produto; falta o link de download assinado.
* **E-mail de confirmação de compra/recibo** e aviso quando o Pix expira.
* **Nota fiscal / CPF completo** — depende de a cliente emitir ou não.
* **LGPD:** não há ainda exportar ou excluir os dados da pessoa, nem política de retenção; antes de ir ao ar, defina com a cliente.
* **Antifraude e 3-D Secure** além do que a operadora faz por padrão; **cupons** além do de primeira compra; **frete** (não se aplica a produto digital).
* **Limite de tentativas em memória:** vale para uma instância. Com várias, troque por Redis (classe `RateLimiter` em `app/security.py`).
* **Migrações do banco** (Alembic): as tabelas são criadas automaticamente; antes de mudar o formato com dados reais, adicione migrações.
* **Painel administrativo:** por enquanto só as rotas `/admin/*` (use pelo `/docs`).
* **Cartão com o Mercado Pago:** a tela gera o token com o SDK deles (`createCardToken`), escrito pela documentação e testado só com um SDK simulado. Confira no sandbox junto com o resto (veja "Antes de ir ao ar").

## Estrutura

```
backend/
├── app/
│   ├── main.py            aplicação, erros, CORS, cabeçalhos
│   ├── config.py          variáveis de ambiente
│   ├── models.py          tabelas
│   ├── schemas.py         formatos de entrada e saída
│   ├── routers/           rotas: auth, catalog, cart, shop (checkout/pedidos/webhooks), me, admin, dev, meta
│   ├── services/          regras: accounts, otp, social, cart, catalog, pricing, orders
│   └── gateways/          base, simulated, mercadopago
├── seed/produtos_demo.json   catálogo de demonstração (gerado de ../site/assets/js/products.js)
├── scripts/gerar_produtos_demo.py
├── tests/                 testes automatizados
├── .env.example · requirements*.txt · dev.sh
```
