/* Criando Memórias — Minha conta: meus kits (GET /me/library) e pedidos (GET /orders). */
(function () {
  "use strict";
  const CM = window.CM, api = window.CMApi, Loja = window.Loja;
  if (!CM || !api || !Loja) return;
  const { $, $$, esc, toast, cover, PRODS } = CM;
  const dlg = $("#conta"), body = $("#conta-body"), foot = $("#conta-foot");
  Loja.wireDialog(dlg);

  const state = { tab: "kits", library: null, orders: null, error: "", confirming: "" };
  const STATUS = { pending: ["Aguardando pagamento", "warn"], paid: ["Pago", "ok"], failed: ["Não aprovado", "bad"], expired: ["Expirado", "muted"], canceled: ["Cancelado", "muted"], refunded: ["Reembolsado", "muted"] };
  const METHOD = { pix: "Pix", boleto: "Boleto", card: "Cartão" };
  const date = (iso) => new Date(iso).toLocaleDateString("pt-BR", { day: "2-digit", month: "short", year: "numeric" });

  function kitsHTML() {
    if (state.error) return `<p class="form-error" role="alert">${esc(state.error)}</p>`;
    if (!state.library) return '<p class="auth-loading" role="status">Carregando…</p>';
    if (!state.library.length) return `<div class="car-empty"><h3>Nenhum kit ainda</h3><p>Quando um pagamento é confirmado, o kit aparece aqui.</p><button class="btn btn-ghost btn-sm" type="button" data-goto="#catalogo">Ver o catálogo</button></div>`;
    return `<ul class="ci-list">${state.library.map((it) => {
      const k = PRODS.find((p) => p.slug === it.product.slug);
      return `<li class="ci"><div class="ci-cover">${k ? cover(k) : '<span class="ci-ph" aria-hidden="true">cm</span>'}</div>
        <div class="ci-info"><p class="ci-meta">${esc(it.product.occasion)}</p><h3>${esc(it.product.name)}</h3>
        <p class="ci-type">Pedido ${esc(it.order_code)} · ${date(it.purchased_at)}</p><p class="kit-note">Os arquivos deste kit serão liberados aqui.</p></div></li>`;
    }).join("")}</ul>`;
  }

  function ordersHTML() {
    if (state.error) return `<p class="form-error" role="alert">${esc(state.error)}</p>`;
    if (!state.orders) return '<p class="auth-loading" role="status">Carregando…</p>';
    if (!state.orders.length) return `<div class="car-empty"><h3>Nenhum pedido ainda</h3><p>Seus pedidos aparecem aqui, com o andamento do pagamento.</p></div>`;
    return `<ul class="ord-list">${state.orders.map((o) => {
      const st = STATUS[o.status] || [o.status, "muted"], names = o.items.map((i) => i.name).join(", ");
      const pending = o.status === "pending";
      return `<li class="ord"><div class="ord-top"><strong>${esc(o.code)}</strong><span class="chip-st is-${st[1]}">${st[0]}</span></div>
        <p class="ord-items">${esc(names)}</p>
        <p class="ord-meta">${date(o.created_at)} · ${esc(METHOD[o.payment_method] || o.payment_method)}${o.installments > 1 ? ` em ${o.installments}x` : ""} · <strong>${Loja.money(o.charged_cents || o.total_cents)}</strong></p>
        ${pending ? `<div class="ord-acts"><button class="btn btn-primary btn-sm" type="button" data-pay="${esc(o.id)}">Ver pagamento</button>
          <button class="btn btn-ghost btn-sm" type="button" data-cancel="${esc(o.id)}">${state.confirming === o.id ? "Confirmar cancelamento" : "Cancelar"}</button></div>` : ""}</li>`;
    }).join("")}</ul>`;
  }

  function render() {
    const u = api.user(); if (!u) return;
    const init = (u.name || u.email || "?").trim().charAt(0).toUpperCase(), contact = u.email || u.phone || "";
    const how = (u.providers || []).length ? `Entrou com ${u.providers.map((p) => ({ google: "Google", facebook: "Facebook", password: "senha", otp: "código" }[p] || p)).join(", ")}` : "";
    body.innerHTML = `<div class="who"><span class="avatar big" aria-hidden="true">${esc(init)}</span><div><strong>${esc(u.name || "Sua conta")}</strong><span>${esc(contact)}</span>${how ? `<small>${esc(how)}</small>` : ""}</div></div>
      <div class="seg" role="group" aria-label="Seção da conta">
        <button type="button" data-tab="kits" aria-pressed="${state.tab === "kits"}">Meus kits</button>
        <button type="button" data-tab="pedidos" aria-pressed="${state.tab === "pedidos"}">Pedidos</button></div>
      <div id="conta-lista" aria-live="polite">${state.tab === "kits" ? kitsHTML() : ordersHTML()}</div>`;
    foot.innerHTML = '<button class="btn btn-ghost btn-sm btn-block" type="button" data-logout>Sair da conta</button>';
  }

  async function load() {
    state.error = "";
    try {
      if (state.tab === "kits") state.library = await api.library(); else state.orders = await api.orders();
    } catch (e) { state.error = Loja.errMsg(e); }
    if (dlg.open) render();
  }

  dlg.addEventListener("click", async (e) => {
    const tab = e.target.closest("[data-tab]");
    if (tab) { state.tab = tab.dataset.tab; state.confirming = ""; render(); load(); return; }
    const pay = e.target.closest("[data-pay]");
    if (pay) { dlg.close(); if (Loja.openOrder) Loja.openOrder(pay.dataset.pay); return; }
    const cancel = e.target.closest("[data-cancel]");
    if (cancel) {
      const id = cancel.dataset.cancel;
      if (state.confirming !== id) { state.confirming = id; render(); return; }
      try { await api.cancelOrder(id); state.confirming = ""; toast("Pedido cancelado."); await load(); }
      catch (err) { state.confirming = ""; toast(Loja.errMsg(err)); load(); }
      return;
    }
    if (e.target.closest("[data-logout]")) { await api.logout(); dlg.close(); toast("Você saiu da conta."); }
  });

  Loja.openAccount = function (tab) {
    state.tab = tab || "kits"; state.error = ""; state.confirming = ""; state.library = null; state.orders = null;
    render(); Loja.showDialog(dlg); load();
  };
})();
