/* Criando Memórias — finalizar compra: dados de quem paga, Pix, cartão (parcelado) e boleto, e o acompanhamento do pedido.
   O número do cartão fica no navegador: ele vira um token na operadora (Mercado Pago) e só o token vai para a API. */
(function () {
  "use strict";
  const CM = window.CM, api = window.CMApi, Loja = window.Loja;
  if (!CM || !api || !Loja) return;
  const { $, $$, esc, toast, cover, PRODS } = CM;
  const dlg = $("#checkout"), main = $("#co-main"), side = $("#co-side");
  Loja.wireDialog(dlg);
  const money = Loja.money;

  const S = { method: "pix", installments: 1, form: {}, order: null, cfg: null, poll: null, clock: null, attempt: null, busy: false, fixed: null };

  /* ---------- formatação e validação ---------- */
  const digits = (v) => String(v || "").replace(/\D/g, "");
  const fmtCpf = (v) => digits(v).slice(0, 11).replace(/^(\d{3})(\d)/, "$1.$2").replace(/^(\d{3})\.(\d{3})(\d)/, "$1.$2.$3").replace(/\.(\d{3})(\d)/, ".$1-$2");
  const fmtPhone = (v) => { const d = digits(v).slice(0, 11); if (d.length <= 2) return d; if (d.length <= 6) return `(${d.slice(0, 2)}) ${d.slice(2)}`; if (d.length <= 10) return `(${d.slice(0, 2)}) ${d.slice(2, 6)}-${d.slice(6)}`; return `(${d.slice(0, 2)}) ${d.slice(2, 7)}-${d.slice(7)}`; };
  const fmtCep = (v) => digits(v).slice(0, 8).replace(/^(\d{5})(\d)/, "$1-$2");
  const fmtCard = (v) => digits(v).slice(0, 19).replace(/(\d{4})(?=\d)/g, "$1 ");
  const fmtExp = (v) => { const d = digits(v).slice(0, 4); return d.length > 2 ? `${d.slice(0, 2)}/${d.slice(2)}` : d; };
  const MASKS = { cpf: fmtCpf, phone: fmtPhone, cep: fmtCep, card: fmtCard, exp: fmtExp, cvv: (v) => digits(v).slice(0, 4), uf: (v) => v.replace(/[^a-zA-Z]/g, "").slice(0, 2).toUpperCase() };
  const localPhone = (p) => { const d = digits(p); return fmtPhone(d.length > 11 && d.startsWith("55") ? d.slice(2) : d); };

  function cpfOk(v) {
    const d = digits(v); if (d.length !== 11 || /^(\d)\1+$/.test(d)) return false;
    for (let t = 9; t < 11; t++) { let s = 0; for (let i = 0; i < t; i++) s += Number(d[i]) * (t + 1 - i); if (((s * 10) % 11) % 10 !== Number(d[t])) return false; }
    return true;
  }
  function luhnOk(n) { let s = 0, alt = false; for (let i = n.length - 1; i >= 0; i--) { let x = Number(n[i]); if (alt) { x *= 2; if (x > 9) x -= 9; } s += x; alt = !alt; } return s % 10 === 0; }
  const uuid = () => (window.crypto && crypto.randomUUID) ? crypto.randomUUID() : ([1e7] + -1e3 + -4e3 + -8e3 + -1e11).replace(/[018]/g, (c) => (c ^ (crypto.getRandomValues(new Uint8Array(1))[0] & (15 >> (c / 4)))).toString(16));
  const guessBrand = (n) => /^4/.test(n) ? "visa" : /^(5[1-5]|2[2-7])/.test(n) ? "master" : /^3[47]/.test(n) ? "amex" : /^(636368|438935|504175|451416|636297|5067|4576|4011|506699)/.test(n) ? "elo" : /^(606282|3841)/.test(n) ? "hipercard" : /^3(0|6|8)/.test(n) ? "diners" : "visa";

  const REJECT = {
    cc_rejected_insufficient_amount: "O cartão não tem limite suficiente.",
    cc_rejected_bad_filled_card_number: "Confira o número do cartão.",
    cc_rejected_bad_filled_date: "Confira a data de validade do cartão.",
    cc_rejected_bad_filled_security_code: "Confira o código de segurança (CVV).",
    cc_rejected_bad_filled_other: "Confira os dados do cartão.",
    cc_rejected_call_for_authorize: "O seu banco precisa autorizar este pagamento. Fale com ele ou use outro cartão.",
    cc_rejected_card_disabled: "O cartão está desativado. Ative-o com o seu banco ou use outro.",
    cc_rejected_duplicated_payment: "Você já fez um pagamento igual a este. Confira em Minha conta, na aba Pedidos.",
    cc_rejected_high_risk: "Não conseguimos aprovar este pagamento. Tente outra forma de pagamento.",
    cc_rejected_max_attempts: "Você atingiu o limite de tentativas. Use outro cartão ou outra forma de pagamento.",
    cc_rejected_other_reason: "O banco não aprovou o pagamento. Tente outro cartão ou outra forma de pagamento.",
    gateway_error: "Não foi possível concluir o pagamento agora. Tente de novo."
  };

  const isSim = () => !!(S.cfg && S.cfg.card && S.cfg.card.provider === "simulated");
  const stopTimers = () => { clearTimeout(S.poll); clearInterval(S.clock); S.poll = S.clock = null; };
  dlg.addEventListener("close", () => { stopTimers(); S.busy = false; });
  const loading = '<p class="auth-loading" role="status">Carregando…</p>';
  const field = (o) => `<div class="field${o.cls ? " " + o.cls : ""}"><label for="${o.id}">${o.label}</label><input id="${o.id}" name="${o.name}" type="${o.type || "text"}" autocomplete="${o.ac || "off"}" ${o.attrs || ""}${o.value ? ` value="${esc(o.value)}"` : ""}>${o.hint ? `<small class="hint">${o.hint}</small>` : ""}<small class="err" hidden></small></div>`;

  /* ---------- resumo (coluna da direita) ---------- */
  function sumBlock(o) {
    return `<h3 class="co-side-h">Resumo do pedido</h3>
      <ul class="sum-items">${o.items.map((i) => `<li><span>${esc(i.name)}</span><span>${money(i.cents)}</span></li>`).join("")}</ul>
      <dl class="sum"><div><dt>Subtotal</dt><dd>${money(o.subtotal)}</dd></div>
        ${o.discount ? `<div class="sum-disc"><dt>Desconto de primeira compra</dt><dd>− ${money(o.discount)}</dd></div>` : ""}
        ${o.interest ? `<div><dt>Juros do parcelamento</dt><dd>${money(o.interest)}</dd></div>` : ""}
        <div class="sum-total"><dt>${esc(o.totalLabel || "Total")}</dt><dd>${money(o.total)}</dd></div></dl>${o.note ? `<p class="sum-inst">${o.note}</p>` : ""}`;
  }
  /* o preço que a tela mostra: o do carrinho, ou o que o servidor corrigiu (S.fixed) quando o desconto não valeu */
  function price() {
    const c = Loja.S.cart;
    return S.fixed || { subtotal: c.subtotal_cents, discount: c.discount_cents, total: c.total_cents, options: c.installment_options };
  }
  function option() { const o = price().options; return o.find((x) => x.installments === S.installments) || o[0]; }
  function sideCart() {
    const c = Loja.S.cart, pr = price(), card = S.method === "card", opt = card ? option() : null;
    side.innerHTML = `<div class="co-side-in">${sumBlock({ items: c.items.map((i) => ({ name: i.product.name, cents: i.product.price_cents })), subtotal: pr.subtotal, discount: pr.discount,
      interest: opt ? opt.total_cents - pr.total : 0, total: opt ? opt.total_cents : pr.total,
      note: opt && opt.installments > 1 ? `${opt.installments}x de <strong>${money(opt.installment_cents)}</strong>${opt.interest_free ? " sem juros" : ""}` : "" })}</div>`;
  }
  function sideOrder(o) {
    const cardN = o.payment_method === "card" && o.installments > 1;
    side.innerHTML = `<div class="co-side-in">${sumBlock({ items: o.items.map((i) => ({ name: i.name, cents: i.unit_price_cents })), subtotal: o.subtotal_cents, discount: o.discount_cents,
      interest: (o.charged_cents || o.total_cents) - o.total_cents, total: o.charged_cents || o.total_cents,
      note: cardN ? `${o.installments}x de <strong>${money(Math.round((o.charged_cents || o.total_cents) / o.installments))}</strong>` : "" })}</div>`;
  }

  /* ---------- formulário ---------- */
  function methodsHTML() {
    const o = price().options, last = o[o.length - 1];
    const cardSub = o.length > 1 ? `Em até ${last.installments}x${o.every((x) => x.interest_free) ? " sem juros" : ""}` : "À vista";
    const days = S.cfg ? S.cfg.boleto_due_days : 3;
    const list = (S.cfg && S.cfg.payment_methods) || ["pix", "boleto", "card"];
    const M = { pix: ["Pix", "Aprovação na hora"], card: ["Cartão de crédito", cardSub], boleto: ["Boleto", `Vence em ${days} dias`] };
    return `<div class="pay-methods" role="radiogroup" aria-label="Forma de pagamento">${["pix", "card", "boleto"].filter((m) => list.includes(m)).map((m) =>
      `<label class="pm"><input type="radio" name="method" value="${m}"${S.method === m ? " checked" : ""}><span class="pm-in"><span class="pm-ico">${PM_ICON[m]}</span><span><strong>${M[m][0]}</strong><small>${M[m][1]}</small></span></span></label>`).join("")}</div>`;
  }
  const PM_ICON = {
    pix: '<svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true"><path d="M12 3.2l3.4 3.4a2 2 0 0 0 1.4.6h.9L20.8 10.3a2 2 0 0 1 0 2.8l-3.1 3.1h-.9a2 2 0 0 0-1.4.6L12 20.2l-3.4-3.4a2 2 0 0 0-1.4-.6h-.9L3.2 13.100a2 2 0 0 1 0-2.800l3.100-3.100h.9a2 2 0 0 0 1.400-.6z" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/></svg>',
    card: '<svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true"><rect x="3" y="5.500" width="18" height="13" rx="2.500" fill="none" stroke="currentColor" stroke-width="1.8"/><path d="M3 10h18M6.500 15h3" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>',
    boleto: '<svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true"><path d="M4 6v12M7.500 6v12M11 6v12M15 6v12M18 6v12M20.500 6v12" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/></svg>'
  };

  const optionsHTML = (opts) => opts.map((o) => `<option value="${o.installments}"${o.installments === S.installments ? " selected" : ""}>${o.installments === 1 ? `À vista · ${money(o.total_cents)}` : `${o.installments}x de ${money(o.installment_cents)}${o.interest_free ? " sem juros" : ` (total ${money(o.total_cents)})`}`}</option>`).join("");
  function extraHTML() {
    const opts = price().options;
    if (S.method === "pix") return `<p class="pm-note">O código Pix é gerado na próxima etapa e vale por ${S.cfg ? S.cfg.pix_expiration_minutes : 30} minutos. Assim que o pagamento é confirmado, o pedido é liberado.</p>`;
    if (S.method === "boleto") return `<p class="pm-note">O boleto vence em ${S.cfg ? S.cfg.boleto_due_days : 3} dias. A compensação pode levar até 2 dias úteis, e o pedido só é liberado depois dela.</p>
      <div class="grid-2">${field({ id: "co-cep", name: "payer.address.zip_code", label: "CEP", ac: "postal-code", attrs: 'inputmode="numeric" data-mask="cep" placeholder="00000-000"', value: S.form.cep })}
        ${field({ id: "co-uf", name: "payer.address.state", label: "Estado (UF)", ac: "address-level1", attrs: 'data-mask="uf" maxlength="2" placeholder="SP"', value: S.form.uf })}
        ${field({ id: "co-rua", name: "payer.address.street", label: "Rua", ac: "address-line1", cls: "full", value: S.form.rua })}
        ${field({ id: "co-num", name: "payer.address.number", label: "Número", ac: "off", value: S.form.num })}
        ${field({ id: "co-comp", name: "payer.address.complement", label: "Complemento (opcional)", ac: "address-line2", value: S.form.comp })}
        ${field({ id: "co-bairro", name: "payer.address.neighborhood", label: "Bairro", ac: "address-level3", value: S.form.bairro })}
        ${field({ id: "co-cidade", name: "payer.address.city", label: "Cidade", ac: "address-level2", value: S.form.cidade })}</div>`;
    return `${isSim() ? `<p class="dev-box"><strong>Modo de teste:</strong> ninguém é cobrado. Use <strong>4242 4242 4242 4242</strong> para aprovar, <strong>4000 0000 0000 0002</strong> para recusar ou <strong>4000 0000 0000 0259</strong> para ficar em análise, com validade futura e CVV qualquer. <button class="link-btn" type="button" data-fill-card>Preencher cartão de teste</button></p>` : ""}
      <div class="grid-2">${field({ id: "co-cnum", name: "card.number", label: "Número do cartão", ac: "cc-number", cls: "full", attrs: 'inputmode="numeric" data-mask="card" placeholder="0000 0000 0000 0000"' })}
        ${field({ id: "co-cnome", name: "card.name", label: "Nome como está no cartão", ac: "cc-name", cls: "full" })}
        ${field({ id: "co-cexp", name: "card.exp", label: "Validade", ac: "cc-exp", attrs: 'inputmode="numeric" data-mask="exp" placeholder="MM/AA"' })}
        ${field({ id: "co-ccvv", name: "card.cvv", label: "CVV", ac: "cc-csc", attrs: 'inputmode="numeric" data-mask="cvv" placeholder="000"' })}
        ${opts.length > 1 ? `<div class="field full"><label for="co-parc">Parcelas</label><select id="co-parc" name="installments">${optionsHTML(opts)}</select></div>` : ""}</div>
      <p class="pm-note">Os dados do cartão são enviados direto para a operadora de pagamento. Nós não guardamos o número do seu cartão.</p>`;
  }

  function payLabel() {
    const pr = price();
    if (S.method === "pix") return `Pagar com Pix · ${money(pr.total)}`;
    if (S.method === "boleto") return `Gerar boleto · ${money(pr.total)}`;
    const o = option();
    return o.installments > 1 ? `Pagar em ${o.installments}x · ${money(o.total_cents)}` : `Pagar ${money(o.total_cents)}`;
  }
  function paintMethod() {
    $("#co-extra").innerHTML = extraHTML();
    $("#co-pay").textContent = payLabel();
    sideCart();
  }

  function repaintPrice() {
    const sel = $("#co-parc"); if (sel) sel.innerHTML = optionsHTML(price().options);
    $("#co-pay").textContent = payLabel(); sideCart();
  }

  function renderForm() {
    stopTimers(); S.order = null;
    const f = S.form;
    main.innerHTML = `<header class="co-head"><p class="eyebrow">Finalizar compra</p><h2 id="co-titulo">Pagamento</h2></header>
      <form class="form co-form" id="co-form" novalidate>
        <fieldset class="co-sec"><legend><span class="step">1</span>Quem está pagando</legend>
          <div class="grid-2">
            ${field({ id: "co-nome", name: "payer.name", label: "Nome completo", ac: "name", cls: "full", value: f.name })}
            ${field({ id: "co-email", name: "payer.email", label: "E-mail", type: "email", ac: "email", cls: "full", value: f.email, hint: "O comprovante e o acompanhamento do pedido são enviados para ele." })}
            ${field({ id: "co-cpf", name: "payer.cpf", label: "CPF", ac: "off", attrs: 'inputmode="numeric" data-mask="cpf" placeholder="000.000.000-00"', value: f.cpf })}
            ${field({ id: "co-tel", name: "payer.phone", label: "Celular (opcional)", type: "tel", ac: "tel", attrs: 'inputmode="tel" data-mask="phone" placeholder="(11) 98765-4321"', value: f.phone })}
          </div></fieldset>
        <fieldset class="co-sec"><legend><span class="step">2</span>Como você quer pagar</legend>
          ${methodsHTML()}<div id="co-extra"></div></fieldset>
        <p class="form-error" role="alert" hidden></p>
        <button class="btn btn-primary btn-block btn-lg" type="submit" id="co-pay"></button>
        <p class="co-safe">Pagamento processado pela operadora. O preço e o desconto são conferidos pela loja antes de cobrar.</p>
      </form>`;
    paintMethod();
    const first = $("#co-nome"); if (first && !matchMedia("(pointer: coarse)").matches && !first.value) first.focus({ preventScroll: true });
  }

  /* ---------- erros ---------- */
  function clearErrors(form) {
    $$(".field", form).forEach((f) => { f.classList.remove("has-error"); const s = $(".err", f); if (s) { s.hidden = true; s.textContent = ""; } });
    const fe = $(".form-error", form); if (fe) { fe.hidden = true; fe.textContent = ""; }
  }
  function showErrors(form, fields, general) {
    let first = null, rest = general || "";
    Object.keys(fields || {}).forEach((k) => {
      const input = form.elements[k] || form.elements[k.split(".").pop()];
      if (!input || !input.closest) { rest = rest || fields[k]; return; }
      const f = input.closest(".field"), s = $(".err", f);
      f.classList.add("has-error"); s.textContent = fields[k]; s.hidden = false; first = first || input;
    });
    const fe = $(".form-error", form); if (rest && fe) { fe.textContent = rest; fe.hidden = false; }
    const target = first || (rest ? fe : null);
    if (target) target.scrollIntoView({ block: "center", behavior: CM.prefersReduced ? "auto" : "smooth" });
    if (first) first.focus({ preventScroll: true });
  }

  function collect(form) {
    const g = (n) => (form.elements[n] ? form.elements[n].value.trim() : "");
    return { name: g("payer.name"), email: g("payer.email"), cpf: g("payer.cpf"), phone: g("payer.phone"),
      address: { zip_code: g("payer.address.zip_code"), street: g("payer.address.street"), number: g("payer.address.number"), complement: g("payer.address.complement"),
        neighborhood: g("payer.address.neighborhood"), city: g("payer.address.city"), state: g("payer.address.state") },
      card: { number: digits(g("card.number")), name: g("card.name"), exp: g("card.exp"), cvv: g("card.cvv") } };
  }
  function validate(v) {
    const e = {};
    if (v.name.split(/\s+/).filter(Boolean).length < 2) e["payer.name"] = "Informe nome e sobrenome.";
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v.email)) e["payer.email"] = "Informe um e-mail válido.";
    if (!cpfOk(v.cpf)) e["payer.cpf"] = "CPF inválido.";
    if (v.phone && ![10, 11].includes(digits(v.phone).length)) e["payer.phone"] = "Informe o celular com DDD.";
    if (S.method === "card") {
      const c = v.card, [mm, yy] = c.exp.split("/"), now = new Date();
      if (c.number.length < 13 || c.number.length > 19 || !luhnOk(c.number)) e["card.number"] = "Número do cartão inválido.";
      if (c.name.length < 3) e["card.name"] = "Informe o nome como está no cartão.";
      if (!/^\d{2}\/\d{2}$/.test(c.exp) || Number(mm) < 1 || Number(mm) > 12 || new Date(2000 + Number(yy), Number(mm), 1) <= now) e["card.exp"] = "Validade inválida.";
      if (!/^\d{3,4}$/.test(c.cvv)) e["card.cvv"] = "CVV inválido.";
    }
    if (S.method === "boleto") {
      const a = v.address;
      if (digits(a.zip_code).length !== 8) e["payer.address.zip_code"] = "Informe o CEP com 8 números.";
      if (a.street.length < 2) e["payer.address.street"] = "Informe a rua.";
      if (!a.number) e["payer.address.number"] = "Informe o número.";
      if (a.neighborhood.length < 2) e["payer.address.neighborhood"] = "Informe o bairro.";
      if (a.city.length < 2) e["payer.address.city"] = "Informe a cidade.";
      if (!/^[A-Za-z]{2}$/.test(a.state)) e["payer.address.state"] = "Use a sigla do estado.";
    }
    return e;
  }

  /* ---------- cartão: gerar o token na operadora ---------- */
  async function tokenize(card, cpf) {
    const cfg = S.cfg || await api.config();
    const prov = cfg.card && cfg.card.provider, pk = cfg.card && cfg.card.public_key;
    if (prov === "mercadopago") {
      if (!pk) throw new api.ApiError(0, "card_unavailable", "O pagamento com cartão ainda não está disponível. Use Pix ou boleto.");
      try {
        await Loja.loadScript("https://sdk.mercadopago.com/js/v2");
        const mp = new window.MercadoPago(pk, { locale: "pt-BR" }), [mm, yy] = card.exp.split("/");
        const t = await mp.createCardToken({ cardNumber: card.number, cardholderName: card.name, cardExpirationMonth: mm, cardExpirationYear: "20" + yy, securityCode: card.cvv, identificationType: "CPF", identificationNumber: cpf });
        const pm = await mp.getPaymentMethods({ bin: card.number.slice(0, 8) });
        if (!t || !t.id) throw new Error("sem token");
        return { token: t.id, brand: (pm && pm.results && pm.results[0] && pm.results[0].id) || guessBrand(card.number) };
      } catch (e) {
        throw new api.ApiError(0, "card_token", "Não foi possível validar o cartão. Confira os dados e tente de novo.");
      }
    }
    /* operadora simulada (desenvolvimento): o token de mentira depende do cartão de teste */
    const TEST = { "4242424242424242": "tok_approved", "4000000000000002": "tok_rejected", "4000000000000259": "tok_pending" };
    return { token: TEST[card.number] || "tok_approved", brand: guessBrand(card.number) };
  }

  /* ---------- enviar ---------- */
  function setBusy(on) {
    S.busy = on; const b = $("#co-pay"); if (!b) return;
    b.disabled = on; b.classList.toggle("is-busy", on); b.textContent = on ? "Processando…" : payLabel();
  }

  async function submit(form) {
    if (S.busy) return;
    clearErrors(form);
    const v = collect(form), errs = validate(v);
    if (Object.keys(errs).length) { showErrors(form, errs); return; }
    S.form = Object.assign({}, S.form, { name: v.name, email: v.email, cpf: v.cpf, phone: v.phone, cep: v.address.zip_code, uf: v.address.state, rua: v.address.street, num: v.address.number, comp: v.address.complement, bairro: v.address.neighborhood, cidade: v.address.city });
    setBusy(true);
    try {
      const payer = { name: v.name, email: v.email, cpf: digits(v.cpf) };
      if (v.phone) payer.phone = v.phone;
      if (S.method === "boleto") payer.address = Object.assign({}, v.address, { zip_code: digits(v.address.zip_code), state: v.address.state.toUpperCase() });
      const pr = price(), shown = S.method === "card" ? option().total_cents : pr.total;
      const body = { payment_method: S.method, installments: S.method === "card" ? S.installments : 1, expected_total_cents: shown, payer };
      if (S.method === "card") { const t = await tokenize(v.card, digits(v.cpf)); body.card_token = t.token; body.card_brand = t.brand; }
      /* A chave de idempotência só se repete quando é exatamente o mesmo pedido que ficou sem resposta (queda de rede) */
      const sig = JSON.stringify(body);
      if (!S.attempt || S.attempt.sig !== sig) S.attempt = { sig, key: uuid() };
      let order;
      try { order = await api.checkout(body, S.attempt.key); }
      catch (e) { if (e.status !== 0) S.attempt = null; throw e; }
      S.attempt = null;
      Loja.loadCart(true);
      showOrder(order);
    } catch (e) {
      if (!(e instanceof api.ApiError)) { console.error(e); e = new api.ApiError(0, "unknown", "Algo deu errado. Tente de novo."); }
      if (e.status === 401) { dlg.close(); toast("Sua sessão expirou. Entre de novo para pagar."); Loja.startCheckout(); return; }
      if (e.code === "cart_empty") { dlg.close(); toast(e.message); Loja.loadCart(true); return; }
      if (e.code === "price_changed" && e.details) { await priceChanged(form, e); return; }
      const hint = e.code === "network" && S.method === "card" ? " Se o valor chegou a ser cobrado, o pedido aparece em Minha conta, na aba Pedidos." : "";
      showErrors(form, e.fields, e.message + hint);
    } finally { setBusy(false); }
  }

  /* O servidor não cobrou: o valor é outro (ex.: o desconto de primeira compra não vale para este CPF).
     A tela passa a mostrar o valor certo e a pessoa decide se paga. */
  async function priceChanged(form, e) {
    const d = e.details, before = price().discount;
    let options = []; try { options = await api.installments(d.total_cents); } catch (x) { /* sem parcelas: só à vista */ }
    S.fixed = { subtotal: Loja.S.cart.subtotal_cents, discount: d.discount_cents, total: d.total_cents, options };
    if (!options.some((o) => o.installments === S.installments)) S.installments = 1;
    repaintPrice();
    const why = d.discount_cents < before ? "O desconto de primeira compra não vale para este CPF, porque ele já foi usado em outra compra. " : "";
    showErrors(form, null, `${why}O valor do pedido ficou em ${money(d.charged_cents || d.total_cents)}. Nada foi cobrado. Se estiver de acordo, é só pagar de novo.`);
  }

  /* ---------- telas do pedido ---------- */
  const copyText = (text, btn) => {
    const done = () => { toast("Copiado."); if (btn) { const t = btn.textContent; btn.textContent = "Copiado ✓"; setTimeout(() => { btn.textContent = t; }, 1800); } };
    if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(text).then(done, () => fallbackCopy(text, done));
    else fallbackCopy(text, done);
  };
  function fallbackCopy(text, done) {
    const ta = document.createElement("textarea"); ta.value = text; ta.setAttribute("readonly", ""); ta.style.cssText = "position:fixed;opacity:0";
    document.body.appendChild(ta); ta.select(); try { document.execCommand("copy"); done(); } catch (e) { toast("Não foi possível copiar. Selecione o código e copie."); } ta.remove();
  }
  const head = (o, title) => `<header class="co-head"><p class="eyebrow">Pedido ${esc(o.code)}</p><h2 id="co-titulo">${title}</h2></header>`;
  const simBox = (o) => isSim() ? `<p class="dev-box"><strong>Modo de teste.</strong> Nenhum valor é cobrado. Simular: <button class="link-btn" type="button" data-sim="approve">pagamento aprovado</button> · <button class="link-btn" type="button" data-sim="reject">recusado</button> · <button class="link-btn" type="button" data-sim="expire">expirado</button></p>` : "";
  const safeUrl = (u) => (/^https?:\/\//i.test(u || "") ? u : "");
  const fmtDate = (iso) => { const m = String(iso || "").match(/^(\d{4})-(\d{2})-(\d{2})/); return m ? `${m[3]}/${m[2]}/${m[1]}` : ""; };

  function showOrder(o) {
    stopTimers(); S.order = o; sideOrder(o);
    if (o.status === "paid") return viewPaid(o);
    if (o.status === "pending") { startPoll(); return o.payment_method === "pix" ? viewPix(o) : o.payment_method === "boleto" ? viewBoleto(o) : viewReview(o); }
    if (o.status === "failed") return viewFailed(o);
    return viewClosed(o);
  }

  function viewPix(o) {
    const pix = (o.payment && o.payment.pix) || {}, expires = pix.expires_at ? Date.parse(pix.expires_at) : 0;
    main.innerHTML = `${head(o, "Pague com Pix")}
      <div class="pix">
        <div class="pix-qr" id="pix-qr" aria-live="polite"><span class="qr-wait">Gerando o QR Code…</span></div>
        <div class="pix-info">
          ${expires ? `<p class="pix-timer" id="pix-timer">Este código vale por <strong id="pix-left"></strong></p>` : ""}
          <ol class="steps"><li>Abra o aplicativo do seu banco e escolha pagar com Pix.</li><li>Escaneie o QR Code ou use o Pix copia e cola.</li><li>Confirme o pagamento. Esta tela atualiza sozinha.</li></ol>
        </div>
      </div>
      ${pix.qr_code ? `<div class="copy-row"><label for="pix-code">Pix copia e cola</label><div class="copy"><input id="pix-code" type="text" readonly value="${esc(pix.qr_code)}"><button class="btn btn-primary btn-sm" type="button" data-copy="#pix-code">Copiar código</button></div></div>` : ""}
      <p class="status" id="co-status" role="status"><span class="spinner" aria-hidden="true"></span><span>Aguardando o pagamento…</span></p>
      ${simBox(o)}
      <div class="co-links"><button class="link-btn" type="button" data-back>Escolher outra forma de pagamento</button></div>`;
    drawQr(pix);
    if (expires) {
      const tick = () => {
        const left = Math.max(0, Math.floor((expires - Date.now()) / 1000)), el = $("#pix-left"); if (!el) return;
        el.textContent = `${String(Math.floor(left / 60)).padStart(2, "0")}:${String(left % 60).padStart(2, "0")}`;
        if (!left) { clearInterval(S.clock); $("#pix-timer").innerHTML = "Este Pix expirou."; $("#co-status").innerHTML = '<span>O prazo acabou. Gere um novo Pix para pagar.</span> <button class="btn btn-primary btn-sm" type="button" data-back>Gerar novo Pix</button>'; }
      };
      tick(); S.clock = setInterval(tick, 1000);
    }
  }
  async function drawQr(pix) {
    const slot = $("#pix-qr"); if (!slot) return;
    if (pix.qr_code_base64 && /^[A-Za-z0-9+/=\s]+$/.test(pix.qr_code_base64)) { slot.innerHTML = `<img src="data:image/png;base64,${pix.qr_code_base64.replace(/\s/g, "")}" width="220" height="220" alt="QR Code do Pix">`; return; }
    if (!pix.qr_code) { slot.innerHTML = '<span class="qr-wait">Use o código abaixo.</span>'; return; }
    try {
      await Loja.loadScript("assets/js/vendor/qrcode.js");
      const qr = window.qrcode(0, "M"); qr.addData(pix.qr_code); qr.make();
      slot.innerHTML = qr.createSvgTag({ cellSize: 4, margin: 2, scalable: true });
      const svg = $("svg", slot); if (svg) { svg.setAttribute("role", "img"); svg.setAttribute("aria-label", "QR Code do Pix"); }
    } catch (e) { slot.innerHTML = '<span class="qr-wait">Não foi possível desenhar o QR Code. Use o código abaixo.</span>'; }
  }

  function viewBoleto(o) {
    const b = (o.payment && o.payment.boleto) || {}, url = safeUrl(b.url);
    main.innerHTML = `${head(o, "Boleto gerado")}
      <div class="boleto">
        ${b.due_date ? `<p class="boleto-due">Vencimento <strong>${fmtDate(b.due_date)}</strong></p>` : ""}
        ${b.digitable_line ? `<div class="copy-row"><label for="bol-code">Linha digitável</label><div class="copy"><input id="bol-code" type="text" readonly value="${esc(b.digitable_line)}"><button class="btn btn-primary btn-sm" type="button" data-copy="#bol-code">Copiar</button></div></div>` : ""}
        ${url ? `<a class="btn btn-ghost" href="${esc(url)}" target="_blank" rel="noopener">Abrir o boleto (PDF)</a>` : ""}
        <p class="pm-note">Pague no aplicativo do seu banco ou em casas lotéricas. A compensação pode levar até 2 dias úteis, e o pedido é liberado assim que ela acontece. Pode fechar esta janela: o andamento fica em Minha conta, na aba Pedidos.</p>
      </div>
      <p class="status" id="co-status" role="status"><span class="spinner" aria-hidden="true"></span><span>Aguardando o pagamento…</span> <button class="link-btn" type="button" data-check>Verificar agora</button></p>
      ${simBox(o)}
      <div class="co-links"><button class="link-btn" type="button" data-back>Escolher outra forma de pagamento</button></div>`;
  }

  function viewReview(o) {
    main.innerHTML = `${head(o, "Pagamento em análise")}
      <div class="notice"><p>A operadora do cartão está analisando o pagamento. Pode levar alguns minutos. Esta tela atualiza sozinha, e você também acompanha em Minha conta, na aba Pedidos.</p></div>
      <p class="status" id="co-status" role="status"><span class="spinner" aria-hidden="true"></span><span>Aguardando a confirmação…</span></p>
      ${simBox(o)}`;
  }

  function viewFailed(o) {
    const detail = o.payment && o.payment.status_detail, msg = REJECT[detail] || "O pagamento não foi aprovado. Confira os dados ou use outra forma de pagamento.";
    main.innerHTML = `${head(o, "Pagamento não aprovado")}
      <div class="notice is-bad" role="alert"><p>${esc(msg)}</p><p>Nada foi cobrado. Seu carrinho continua do jeito que estava.</p></div>
      <button class="btn btn-primary btn-block" type="button" data-back>Tentar de novo</button>`;
  }

  function viewClosed(o) {
    const L = { expired: ["Pedido expirado", "O prazo para pagar acabou e o pedido foi encerrado. Seu carrinho continua guardado: é só gerar um novo pagamento."], canceled: ["Pedido cancelado", "Este pedido foi cancelado. Seu carrinho continua guardado."], refunded: ["Pedido reembolsado", "O valor deste pedido foi devolvido."] }[o.status] || ["Pedido", ""];
    main.innerHTML = `${head(o, L[0])}<div class="notice"><p>${L[1]}</p></div>${o.status === "refunded" ? "" : '<button class="btn btn-primary btn-block" type="button" data-back>Voltar ao pagamento</button>'}`;
  }

  function viewPaid(o) {
    Loja.loadCart(true);
    main.innerHTML = `<div class="done"><span class="done-ico" aria-hidden="true"><svg viewBox="0 0 24 24" width="34" height="34"><path d="M5 12.500l4.500 4.500L19 7.500" fill="none" stroke="currentColor" stroke-width="2.400" stroke-linecap="round" stroke-linejoin="round"/></svg></span>
      <p class="eyebrow">Pedido ${esc(o.code)}</p><h2 id="co-titulo">Pagamento confirmado</h2>
      <p class="done-p">Recebemos o seu pagamento de <strong>${money(o.charged_cents || o.total_cents)}</strong>${o.payment_method === "card" && o.installments > 1 ? ` em ${o.installments}x` : ""}. ${o.items.length === 1 ? "O kit fica guardado" : "Os kits ficam guardados"} em Minha conta, na aba Meus kits, e os arquivos serão liberados ali.</p>
      <ul class="done-list">${o.items.map((i) => `<li>${esc(i.name)}</li>`).join("")}</ul>
      <div class="done-acts"><button class="btn btn-primary" type="button" data-kits>Ver meus kits</button><button class="btn btn-ghost" type="button" data-close>Continuar no catálogo</button></div></div>`;
  }

  /* ---------- acompanhar o pagamento ---------- */
  function startPoll() {
    const gap = () => (document.hidden ? 15000 : S.order.payment_method === "pix" ? 4000 : S.order.payment_method === "boleto" ? 15000 : 6000);
    const tick = async () => {
      if (!dlg.open || !S.order) return;
      try { const o = await api.order(S.order.id); if (o.status !== "pending") { showOrder(o); return; } }
      catch (e) { if (e.status === 401 || e.status === 404) return; }
      S.poll = setTimeout(tick, gap());
    };
    S.poll = setTimeout(tick, gap());
  }
  document.addEventListener("visibilitychange", () => { if (!document.hidden && dlg.open && S.order && S.order.status === "pending" && S.poll) { clearTimeout(S.poll); S.poll = setTimeout(() => startPollNow(), 300); } });
  function startPollNow() { const id = S.order && S.order.id; if (!id) return; api.order(id).then((o) => { if (o.status !== "pending") showOrder(o); else startPoll(); }).catch(() => startPoll()); }

  /* ---------- eventos ---------- */
  dlg.addEventListener("input", (e) => {
    const t = e.target, m = t.dataset && t.dataset.mask;
    if (m && MASKS[m]) { const v = MASKS[m](t.value); if (v !== t.value) t.value = v; if (m === "cep" && digits(v).length === 8) lookupCep(digits(v)); }
  });
  dlg.addEventListener("change", (e) => {
    const t = e.target;
    if (t.name === "method") { S.method = t.value; if (t.value !== "card") S.installments = 1; paintMethod(); }
    else if (t.name === "installments") { S.installments = Number(t.value) || 1; $("#co-pay").textContent = payLabel(); sideCart(); }
  });
  dlg.addEventListener("submit", (e) => { e.preventDefault(); if (e.target.id === "co-form") submit(e.target); });
  dlg.addEventListener("click", async (e) => {
    const t = e.target;
    if (t.closest("[data-back]")) { renderForm(); return; }
    const cp = t.closest("[data-copy]"); if (cp) { const i = $(cp.dataset.copy); i.select(); copyText(i.value, cp); return; }
    if (t.closest("[data-kits]")) { dlg.close(); Loja.openAccount("kits"); return; }
    if (t.closest("[data-check]")) { startPollNow(); toast("Verificando o pagamento…"); return; }
    const sim = t.closest("[data-sim]");
    if (sim && S.order) { try { showOrder(await api.simulate(S.order.id, sim.dataset.sim)); } catch (err) { toast(Loja.errMsg(err)); } return; }
    if (t.closest("[data-fill-card]")) {
      const set = (id, v) => { const el = $(id); if (el) el.value = v; };
      set("#co-cnum", "4242 4242 4242 4242"); set("#co-cnome", ($("#co-nome") && $("#co-nome").value) || "TESTE DA SILVA"); set("#co-cexp", `12/${String((new Date().getFullYear() + 3) % 100).padStart(2, "0")}`); set("#co-ccvv", "123");
    }
  });

  /* CEP: preenche rua, bairro, cidade e UF pelo ViaCEP (serviço público e gratuito); se falhar, a pessoa digita */
  let cepAsked = "";
  async function lookupCep(cep) {
    if (cep === cepAsked) return; cepAsked = cep;
    const ctl = new AbortController(), timer = setTimeout(() => ctl.abort(), 4000);
    try {
      const r = await fetch(`https://viacep.com.br/ws/${cep}/json/`, { signal: ctl.signal });
      const d = await r.json(); if (d.erro) return;
      const put = (id, v) => { const el = $(id); if (el && v && !el.value.trim()) el.value = v; };
      put("#co-rua", d.logradouro); put("#co-bairro", d.bairro); put("#co-cidade", d.localidade); put("#co-uf", d.uf);
      const n = $("#co-num"); if (n && !n.value) n.focus({ preventScroll: true });
    } catch (e) { /* sem o serviço: digita à mão */ } finally { clearTimeout(timer); }
  }

  /* ---------- abrir ---------- */
  Loja.openCheckout = async function () {
    if (!api.loggedIn()) return;
    stopTimers(); S.order = null; S.attempt = null; S.fixed = null; side.innerHTML = ""; main.innerHTML = loading;
    Loja.showDialog(dlg);
    let cart, cfg;
    try { [cart, cfg] = await Promise.all([Loja.loadCart(true, true), api.config().catch(() => null)]); }
    catch (e) { main.innerHTML = `<p class="form-error" role="alert">${esc(Loja.errMsg(e))}</p>`; return; }
    S.cfg = cfg || S.cfg;
    if (!cart.items.length) { dlg.close(); toast("Seu carrinho está vazio."); return; }
    const u = api.user() || {}, prev = S.form;
    S.form = Object.assign({ name: u.name || "", email: u.email || "", phone: localPhone(u.phone), cpf: "" }, prev);
    if (S.cfg && S.cfg.payment_methods && !S.cfg.payment_methods.includes(S.method)) S.method = S.cfg.payment_methods[0];
    if (!cart.installment_options.some((o) => o.installments === S.installments)) S.installments = 1;
    renderForm();
  };

  /* abre direto no pagamento de um pedido que ficou pendente (vem de Minha conta > Pedidos) */
  Loja.openOrder = async function (id) {
    stopTimers(); side.innerHTML = ""; main.innerHTML = loading;
    Loja.showDialog(dlg);
    try { S.cfg = S.cfg || await api.config().catch(() => null); showOrder(await api.order(id)); }
    catch (e) { main.innerHTML = `<p class="form-error" role="alert">${esc(Loja.errMsg(e))}</p>`; }
  };
})();
