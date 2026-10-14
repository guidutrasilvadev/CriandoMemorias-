/* Criando Memórias — loja: cabeçalho (conta e carrinho), botões "adicionar" e gaveta do carrinho.
   Depende de api.js e app.js (window.CMApi e window.CM). entrar.js, conta.js e checkout.js completam window.Loja. */
(function () {
  "use strict";
  const CM = window.CM, api = window.CMApi;
  if (!CM || !api) return;
  const { $, $$, esc, toast, cover, PRODS } = CM;
  if (!CM.shopOn) { const c = $("#p-consultar"); if (c) c.className = "btn btn-primary"; return; }

  const money = (cents) => CM.brl(cents / 100);
  const pct = (n) => String(n).replace(".", ",");
  const errMsg = (e) => (e && e.message) || "Algo deu errado. Tente de novo.";
  const EMPTY = { cart_id: null, items: [], items_count: 0, subtotal_cents: 0, discount_cents: 0, total_cents: 0,
    first_purchase_discount: { status: "login_required", percent: 0, estimated_amount_cents: 0 }, installment_options: [], unavailable_product_ids: [] };
  const S = { cart: EMPTY, config: null, loaded: false };
  const Loja = window.Loja = { S, money, pct, errMsg };

  /* scripts de terceiros (Google, Facebook, Mercado Pago, QR Code) só são baixados quando a tela precisa deles */
  const scripts = {};
  Loja.loadScript = (src) => scripts[src] || (scripts[src] = new Promise((ok, fail) => {
    const s = document.createElement("script"); s.src = src; s.async = true; s.onload = ok;
    s.onerror = () => { delete scripts[src]; fail(new Error("script")); };
    document.head.appendChild(s);
  }));

  /* ---------- janelas: fechar no fundo, no X, e devolver a rolagem ---------- */
  Loja.wireDialog = function (d) {
    let down = null;
    d.addEventListener("pointerdown", (e) => { down = e.target; });
    d.addEventListener("click", (e) => { if ((e.target === d && down === d) || e.target.closest("[data-close]")) d.close(); });
    d.addEventListener("close", CM.syncScroll);
  };
  Loja.showDialog = function (d) { if (!d.open) d.showModal(); document.body.style.overflow = "hidden"; CM.raiseToast(); };

  const cartBtn = $("#btn-carrinho"), cartDlg = $("#carrinho"), acctBtn = $("#btn-conta");
  Loja.wireDialog(cartDlg);

  /* ---------- carrinho: estado ---------- */
  const inCart = (id) => S.cart.items.some((i) => i.product.id === id);
  Loja.inCart = inCart;

  function badge() {
    const n = S.cart.items_count, el = $("#cart-count");
    el.hidden = n === 0; el.textContent = n > 9 ? "9+" : String(n);
    cartBtn.setAttribute("aria-label", n ? `Abrir o carrinho, ${n} ${n === 1 ? "kit" : "kits"}` : "Abrir o carrinho, vazio");
  }
  function bump() { cartBtn.classList.remove("bump"); void cartBtn.offsetWidth; cartBtn.classList.add("bump"); }

  /* botões "adicionar" dos cartões e da página do kit */
  function mark() {
    $$("[data-add]").forEach((b) => {
      const id = Number(b.dataset.add), on = inCart(id), k = PRODS.find((p) => p.id === id), nome = k ? k.nome : "o kit";
      b.classList.toggle("is-in", on); b.setAttribute("aria-pressed", String(on));
      const label = on ? `${nome} está no carrinho. Abrir o carrinho` : `Adicionar ${nome} ao carrinho`;
      b.setAttribute("aria-label", label); b.title = on ? "No carrinho" : "Adicionar ao carrinho";
    });
    const k = CM.currentKit(), pa = $("#p-add");
    if (k && pa) { const on = inCart(k.id); pa.textContent = on ? "Ver no carrinho" : "Adicionar ao carrinho"; pa.classList.toggle("is-in", on); }
  }

  /* linha do desconto na página do kit */
  function perkLine() {
    const el = $("#p-perk"); if (!el) return;
    const p = S.config ? S.config.first_purchase_discount_percent : 0, st = S.cart.first_purchase_discount.status;
    if (!p || st === "used" || st === "disabled" || (api.loggedIn() && !S.loaded)) { el.hidden = true; return; }
    el.innerHTML = api.loggedIn() && st === "eligible"
      ? `<strong>${pct(p)}% de desconto</strong> na sua primeira compra, aplicado no carrinho.`
      : `<strong>Ganhe ${pct(p)}% de desconto</strong> na primeira compra. <button class="link-btn" type="button" data-login>Entrar ou criar conta</button>`;
    el.hidden = false;
  }

  function refresh() {
    badge(); mark(); perkLine();
    if (cartDlg.open) renderCart();
    document.dispatchEvent(new Event("cm:cart"));
  }

  /* quiet: não avisa em caso de erro · strict: repassa o erro a quem chamou (o pagamento precisa saber) */
  Loja.loadCart = async function (quiet, strict) {
    if (!api.loggedIn() && !api.hasGuestCart()) { S.cart = EMPTY; S.loaded = true; refresh(); return S.cart; }
    try { S.cart = await api.cart.get(); S.loaded = true; }
    catch (e) { if (strict) throw e; if (!quiet) toast(errMsg(e)); }
    refresh(); return S.cart;
  };

  async function add(id) {
    if (inCart(id)) { openCart(); return; }
    const btns = $$(`[data-add="${id}"]`); btns.forEach((b) => b.classList.add("is-busy"));
    try {
      S.cart = await api.cart.add(id); S.loaded = true; refresh(); bump();
      const k = PRODS.find((p) => p.id === id);
      toast(`${k ? `“${k.nome}”` : "O kit"} foi para o carrinho.`);
    } catch (e) { toast(errMsg(e)); }
    finally { btns.forEach((b) => b.classList.remove("is-busy")); }
  }
  async function remove(id) {
    try { S.cart = await api.cart.remove(id); refresh(); } catch (e) { toast(errMsg(e)); }
  }
  Loja.add = add;

  /* ---------- carrinho: gaveta ---------- */
  const ICON_BAG_BIG = '<svg viewBox="0 0 64 64" width="64" height="64" aria-hidden="true"><path d="M14 22h36l3 32H11z" fill="#9DD2C8" fill-opacity=".45" stroke="#B9A5C1" stroke-width="2.5" stroke-linejoin="round"/><path d="M22 22v-4a10 10 0 0 1 20 0v4" fill="none" stroke="#B9A5C1" stroke-width="2.5" stroke-linecap="round"/></svg>';

  function perkBanner(c) {
    const d = c.first_purchase_discount, p = d.percent || (S.config ? S.config.first_purchase_discount_percent : 0);
    if (d.status === "login_required" && p) {
      const sub = c.items.length && d.estimated_amount_cents ? `Entre ou crie sua conta e economize cerca de ${money(d.estimated_amount_cents)} neste pedido.` : "Entre ou crie sua conta para usar no seu primeiro pedido.";
      return `<aside class="perk-card"><span class="perk-badge" aria-hidden="true">${pct(p)}%</span><div><strong>Ganhe ${pct(p)}% de desconto na primeira compra</strong><span>${sub}</span></div><button class="btn btn-primary btn-sm" type="button" data-login>Entrar</button></aside>`;
    }
    if (d.status === "eligible" && c.items.length) return `<aside class="perk-card is-on"><span class="perk-badge" aria-hidden="true">✓</span><div><strong>Desconto de primeira compra aplicado</strong><span>Você economiza ${money(c.discount_cents)} neste pedido.</span></div></aside>`;
    return "";
  }

  function renderCart() {
    const c = S.cart, body = $("#car-body"), foot = $("#car-foot");
    if (!c.items.length) {
      body.innerHTML = `<div class="car-empty">${ICON_BAG_BIG}<h3>Seu carrinho está vazio</h3><p>Escolha um kit no catálogo e ele fica guardado aqui.</p><button class="btn btn-ghost btn-sm" type="button" data-goto="#catalogo">Ver o catálogo</button></div>${perkBanner(c)}`;
      foot.hidden = true; foot.innerHTML = ""; return;
    }
    const notice = c.unavailable_product_ids.length ? `<p class="car-notice" role="status">Algum kit do seu carrinho não está mais disponível e ficou de fora do total.</p>` : "";
    const items = c.items.map((i) => {
      const k = PRODS.find((p) => p.slug === i.product.slug), prod = i.product;
      return `<li class="ci"><div class="ci-cover">${k ? cover(k) : '<span class="ci-ph" aria-hidden="true">cm</span>'}</div>
        <div class="ci-info"><p class="ci-meta">${esc(prod.occasion)}</p><h3>${esc(prod.name)}</h3><p class="ci-type">${esc(prod.type_label)}</p></div>
        <div class="ci-side"><p class="ci-price">${money(prod.price_cents)}</p><button class="ci-remove" type="button" data-remove="${prod.id}" aria-label="Remover ${esc(prod.name)} do carrinho">Remover</button></div></li>`;
    }).join("");
    body.innerHTML = `${notice}<ul class="ci-list">${items}</ul>${perkBanner(c)}`;
    const o = c.installment_options, last = o[o.length - 1];
    const inst = o.length > 1 ? `<p class="sum-inst">ou até <strong>${last.installments}x de ${money(last.installment_cents)}</strong>${last.interest_free ? " sem juros" : ""} no cartão</p>` : "";
    const d = c.first_purchase_discount;
    foot.hidden = false;
    foot.innerHTML = `<dl class="sum">
        <div><dt>Subtotal</dt><dd>${money(c.subtotal_cents)}</dd></div>
        ${c.discount_cents ? `<div class="sum-disc"><dt>Desconto de primeira compra${d.percent ? ` (${pct(d.percent)}%)` : ""}</dt><dd>− ${money(c.discount_cents)}</dd></div>` : ""}
        <div class="sum-total"><dt>Total</dt><dd>${money(c.total_cents)}</dd></div></dl>${inst}
      <button class="btn btn-primary btn-block" type="button" data-checkout>Finalizar compra</button>
      <button class="btn btn-ghost btn-sm btn-block" type="button" data-close>Continuar escolhendo</button>`;
  }

  function openCart() {
    if (CM.currentKit()) CM.closeProduct();
    renderCart(); Loja.showDialog(cartDlg); Loja.loadCart(true);
  }
  Loja.openCart = openCart;

  /* ---------- ir para o pagamento (pede login antes) ---------- */
  Loja.startCheckout = async function () {
    cartDlg.close();
    if (!api.loggedIn()) {
      const u = await Loja.openAuth({ reason: "Para finalizar a compra, entre ou crie sua conta. O carrinho continua como está." });
      if (!u) return;
    }
    if (Loja.openCheckout) Loja.openCheckout();
  };

  /* ---------- conta no cabeçalho ---------- */
  const personIcon = $("#conta-ico").innerHTML;
  function paintUser(u) {
    const lbl = $("#conta-label"), ico = $("#conta-ico");
    if (u) {
      const first = (u.name || "").trim().split(/\s+/)[0] || "Conta";
      lbl.textContent = first; ico.innerHTML = `<span class="avatar" aria-hidden="true">${esc(first.charAt(0).toUpperCase())}</span>`;
      acctBtn.setAttribute("aria-label", `Minha conta, ${first}`); acctBtn.classList.add("is-in");
    } else {
      lbl.textContent = "Entrar"; ico.innerHTML = personIcon;
      acctBtn.setAttribute("aria-label", "Entrar na sua conta"); acctBtn.classList.remove("is-in");
    }
  }
  api.onChange((u, why) => {
    paintUser(u);
    if (why === "expired" || why === "logout" || why === "sync") {
      if (!u) { const cd = $("#conta"); if (cd && cd.open) cd.close(); S.loaded = false; }
      if (why === "expired") toast("Sua sessão expirou. Entre de novo para continuar.");
      Loja.loadCart(true);
    }
  });

  /* ---------- cliques ---------- */
  document.addEventListener("click", (e) => {
    const t = e.target;
    const a = t.closest("[data-add]"); if (a) { e.preventDefault(); add(Number(a.dataset.add)); return; }
    const r = t.closest("[data-remove]"); if (r) { remove(Number(r.dataset.remove)); return; }
    if (t.closest("[data-checkout]")) { Loja.startCheckout(); return; }
    if (t.closest("[data-login]")) {
      const wasCart = cartDlg.open; if (wasCart) cartDlg.close();
      Loja.openAuth({}).then((u) => { if (wasCart && u) openCart(); });
      return;
    }
    const g = t.closest("[data-goto]");
    if (g) { const el = $(g.dataset.goto); $$("dialog[open]").forEach((d) => d.close()); if (el) el.scrollIntoView({ behavior: CM.prefersReduced ? "auto" : "smooth" }); }
  });
  cartBtn.addEventListener("click", openCart);
  acctBtn.addEventListener("click", () => { if (api.loggedIn()) Loja.openAccount(); else Loja.openAuth({}); });
  $("#p-add").addEventListener("click", () => { const k = CM.currentKit(); if (!k) return; if (inCart(k.id)) openCart(); else add(k.id); });
  document.addEventListener("cm:cards", mark);
  document.addEventListener("cm:produto", () => { mark(); perkLine(); });

  /* ---------- começo ---------- */
  paintUser(api.user());
  badge(); mark();
  api.config().then((c) => { S.config = c; perkLine(); if (cartDlg.open) renderCart(); }).catch(() => { /* API fora do ar: o catálogo continua funcionando */ });
  api.validate().catch(() => {}).then(() => Loja.loadCart(true));
})();
