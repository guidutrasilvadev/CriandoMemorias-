/* Criando Memórias — cliente da API da loja (fetch puro, sem build).
   Guarda a sessão no navegador, renova o token sozinho (uma renovação por vez, inclusive entre abas) e traduz os erros.
   O número do cartão nunca passa por aqui: só o token gerado pela operadora (veja checkout.js). */
(function () {
  "use strict";
  const BASE = String((window.SITE && window.SITE.api) || "").replace(/\/+$/, "");
  const K_SESSION = "cm-sessao", K_CART = "cm-carrinho";

  /* localStorage pode estar bloqueado (aba anônima, política do navegador): nesse caso a sessão vive só na memória */
  const memory = {};
  const disk = {
    get(k) { try { return localStorage.getItem(k); } catch (e) { return memory[k] || null; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch (e) { memory[k] = v; } },
    del(k) { try { localStorage.removeItem(k); } catch (e) { /* ok */ } delete memory[k]; }
  };

  class ApiError extends Error {
    constructor(status, code, message, fields, details) {
      super(message); this.name = "ApiError"; this.status = status; this.code = code; this.fields = fields || null; this.details = details || null;
    }
  }

  /* ---------- sessão ---------- */
  const readSession = () => { try { return JSON.parse(disk.get(K_SESSION) || "null"); } catch (e) { return null; } };
  let session = readSession();
  const watchers = [];
  const notify = (why) => watchers.forEach((fn) => { try { fn(session ? session.user : null, why); } catch (e) { console.error(e); } });
  function setSession(s, why) { session = s; if (s) disk.set(K_SESSION, JSON.stringify(s)); else disk.del(K_SESSION); notify(why); }
  function adopt(t, why) {
    setSession({ access: t.access_token, refresh: t.refresh_token, exp: Date.now() + Math.max(t.expires_in - 10, 5) * 1000, user: t.user }, why || "login");
    return t;
  }
  window.addEventListener("storage", (e) => { if (e.key === K_SESSION) { session = readSession(); notify("sync"); } });

  /* ---------- chamadas ---------- */
  async function send(method, path, o) {
    const headers = { Accept: "application/json" };
    if (o.body !== undefined) headers["Content-Type"] = "application/json";
    if (o.auth !== false && session && session.access) headers.Authorization = "Bearer " + session.access;
    const cartId = disk.get(K_CART);
    if (cartId && o.cart !== false) headers["X-Cart-Id"] = cartId;
    if (o.idem) headers["Idempotency-Key"] = o.idem;
    const ctl = new AbortController(), timer = setTimeout(() => ctl.abort(), o.timeout || 25000);
    let res;
    try {
      res = await fetch(BASE + path, { method, headers, body: o.body !== undefined ? JSON.stringify(o.body) : undefined, signal: ctl.signal, cache: "no-store" });
    } catch (e) {
      console.warn("[loja] Sem resposta da API em " + (BASE || location.origin) + ". Em desenvolvimento: cd backend && ./dev.sh e abra http://localhost:8100");
      throw new ApiError(0, "network", ctl.signal.aborted ? "A loja demorou para responder. Tente de novo." : "Não foi possível falar com a loja. Confira sua internet e tente de novo.");
    } finally { clearTimeout(timer); }
    let data = null;
    try { const text = await res.text(); data = text ? JSON.parse(text) : null; } catch (e) { data = null; } /* lê sempre o corpo, até no 204 */
    if (!res.ok) {
      const er = (data && data.error) || {};
      throw new ApiError(res.status, er.code || "http_" + res.status, er.message || "Não foi possível concluir. Tente de novo.", er.fields, er.details);
    }
    return data;
  }

  async function request(method, path, o) {
    o = o || {};
    const authed = o.auth !== false && !!session;
    if (authed && session.exp - Date.now() < 15000) await refresh();
    try { return await send(method, path, o); }
    catch (e) {
      if (e.status === 401 && authed && !o.retried && (await refresh())) return send(method, path, Object.assign({}, o, { retried: true }));
      throw e;
    }
  }

  /* O refresh token é de uso único (reaproveitar derruba todas as sessões). Por isso: uma renovação por vez, e antes de
     renovar olha se outra aba já renovou. */
  let inflight = null;
  function refresh() {
    if (!session || !session.refresh) return Promise.resolve(false);
    if (inflight) return inflight;
    const run = async () => {
      const stored = readSession();
      if (stored && session && stored.refresh !== session.refresh) {
        session = stored; notify("sync");
        if (stored.exp - Date.now() > 15000) return true;
      }
      if (!session) return false;
      try {
        adopt(await send("POST", "/auth/refresh", { body: { refresh_token: session.refresh }, auth: false, cart: false }), "refresh");
        return true;
      } catch (e) {
        if (e.status === 401 || e.status === 422) setSession(null, "expired"); /* sem rede: mantém a sessão e tenta depois */
        return false;
      }
    };
    inflight = (navigator.locks ? navigator.locks.request("cm-refresh", run) : run()).finally(() => { inflight = null; });
    return inflight;
  }

  const get = (path, o) => request("GET", path, o);
  const post = (path, body, o) => request("POST", path, Object.assign({ body }, o));
  const del = (path, o) => request("DELETE", path, o);
  const memo = (fn) => { let p = null; return () => p || (p = fn().catch((e) => { p = null; throw e; })); };
  /* Carrinho de visitante: guarda o id; logado, o carrinho é da conta e o id some (a primeira chamada logada mescla os dois) */
  const keep = (c) => { if (session) disk.del(K_CART); else if (c && c.cart_id) disk.set(K_CART, c.cart_id); return c; };
  const open = { auth: false };
  const enter = (t) => adopt(t, "login");

  window.CMApi = {
    ApiError, base: BASE,
    user: () => (session ? session.user : null),
    loggedIn: () => !!session,
    hasGuestCart: () => !!disk.get(K_CART),
    onChange: (fn) => { watchers.push(fn); },

    config: memo(() => get("/config/public", { auth: false, cart: false })),
    benefits: memo(() => get("/auth/benefits", { auth: false, cart: false })),

    cart: {
      get: () => get("/cart").then(keep),
      add: (id) => post("/cart/items", { product_id: id }).then(keep),
      remove: (id) => del("/cart/items/" + id).then(keep)
    },

    login: (identifier, password) => post("/auth/login", { identifier, password }, open).then(enter),
    register: (body) => post("/auth/register", body, open).then(enter),
    otpRequest: (destination, channel) => post("/auth/otp/request", { destination, channel }, open),
    otpVerify: (destination, code, name) => post("/auth/otp/verify", name ? { destination, code, name } : { destination, code }, open).then(enter),
    google: (idToken) => post("/auth/google", { id_token: idToken }, open).then(enter),
    facebook: (accessToken) => post("/auth/facebook", { access_token: accessToken }, open).then(enter),
    async logout() {
      const r = session && session.refresh;
      setSession(null, "logout"); disk.del(K_CART);
      if (r) { try { await send("POST", "/auth/logout", { body: { refresh_token: r }, auth: false, cart: false }); } catch (e) { /* já saiu daqui */ } }
    },
    /* confere no servidor se a sessão guardada ainda vale e atualiza os dados */
    validate() {
      if (!session) return Promise.resolve(null);
      return get("/me", { cart: false }).then((u) => { if (session) setSession(Object.assign({}, session, { user: u }), "refresh"); return u; });
    },

    library: () => get("/me/library", { cart: false }),
    orders: () => get("/orders", { cart: false }),
    order: (id) => get("/orders/" + encodeURIComponent(id), { cart: false }),
    cancelOrder: (id) => post("/orders/" + encodeURIComponent(id) + "/cancel", undefined, { cart: false }),
    installments: (amountCents) => get("/payments/installments?amount_cents=" + Number(amountCents), { auth: false, cart: false }),
    checkout: (body, idem) => post("/checkout", body, { idem, timeout: 60000 }),
    /* só existe com a API em desenvolvimento e o pagamento simulado: approve | reject | expire */
    simulate: (id, action) => post("/dev/orders/" + encodeURIComponent(id) + "/" + action, undefined, { cart: false })
  };
})();
