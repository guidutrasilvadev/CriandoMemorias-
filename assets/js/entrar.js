/* Criando Memórias — tela de entrar / criar conta, com os benefícios de ter conta (vêm de GET /auth/benefits).
   Login por e-mail ou telefone + senha, por código (e-mail, SMS, WhatsApp), Google e Facebook. */
(function () {
  "use strict";
  const CM = window.CM, api = window.CMApi, Loja = window.Loja;
  if (!CM || !api || !Loja) return;
  const { $, $$, esc, toast } = CM;
  const dlg = $("#entrar"), perks = $("#auth-perks"), main = $("#auth-main");
  Loja.wireDialog(dlg);

  const state = { view: "entrar", reason: "", benefits: null, config: null, channel: "email", otp: null, resolve: null };

  /* ---------- ícones ---------- */
  const SVG = (inner, size) => `<svg viewBox="0 0 24 24" width="${size || 22}" height="${size || 22}" aria-hidden="true">${inner}</svg>`;
  const ICONS = {
    first_purchase_discount: SVG('<path d="M5 19L19 5" stroke="currentColor" stroke-width="2" stroke-linecap="round" fill="none"/><circle cx="7.5" cy="7.5" r="2.6" fill="none" stroke="currentColor" stroke-width="2"/><circle cx="16.5" cy="16.5" r="2.6" fill="none" stroke="currentColor" stroke-width="2"/>'),
    saved_cart: SVG('<path d="M6 8.5h12l1 11.5H5z" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linejoin="round"/><path d="M9 8.5V7a3 3 0 0 1 6 0v1.5" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round"/>'),
    orders_library: SVG('<path d="M5 5.5A1.5 1.5 0 0 1 6.5 4H19v14.5H6.5A1.5 1.5 0 0 0 5 20z" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linejoin="round"/><path d="M5 20a1.5 1.5 0 0 0 1.5 1H19" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round"/>'),
    _: SVG('<path d="M5 12.5l4.5 4.5L19 7.5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>')
  };
  const GOOGLE = '<svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"><path fill="#4285F4" d="M22.5 12.3c0-.8-.1-1.5-.2-2.2H12v4.2h5.9a5 5 0 0 1-2.2 3.3v2.7h3.5c2.1-1.9 3.3-4.700 3.3-8z"/><path fill="#34A853" d="M12 23c3 0 5.500-1 7.300-2.700l-3.500-2.700c-1 .7-2.200 1.100-3.800 1.100-2.900 0-5.400-2-6.300-4.600H2.100v2.800A11 11 0 0 0 12 23z"/><path fill="#FBBC05" d="M5.700 14.100a6.600 6.600 0 0 1 0-4.200V7.100H2.100a11 11 0 0 0 0 9.800z"/><path fill="#EA4335" d="M12 5.400c1.600 0 3.100.6 4.300 1.700l3.200-3.200A11 11 0 0 0 2.100 7.100l3.600 2.800C6.600 7.400 9.100 5.400 12 5.400z"/></svg>';
  const FACEBOOK = '<svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"><path fill="#1877F2" d="M24 12a12 12 0 1 0-13.900 11.900v-8.400H7.100V12h3V9.400c0-3 1.800-4.700 4.500-4.700 1.300 0 2.700.2 2.700.2v3h-1.500c-1.500 0-2 .9-2 1.900V12h3.400l-.5 3.500h-2.800v8.400A12 12 0 0 0 24 12z"/></svg>';
  const EYE = SVG('<path d="M2.5 12S6 5.500 12 5.500 21.500 12 21.500 12 18 18.500 12 18.500 2.500 12 2.500 12z" fill="none" stroke="currentColor" stroke-width="1.8"/><circle cx="12" cy="12" r="3" fill="none" stroke="currentColor" stroke-width="1.8"/>', 20);

  const loadScript = Loja.loadScript;

  /* ---------- painel dos benefícios ---------- */
  const FALLBACK = { headline: "Entre para comprar com mais vantagens", benefits: [], providers: [], fine_print: "" };
  function renderPerks() {
    const b = state.benefits || FALLBACK;
    perks.innerHTML = `<img class="auth-logo" src="assets/img/logo-cm-240.webp" width="84" height="51" alt="">
      <p class="eyebrow">Sua conta</p>
      <h2 id="auth-titulo">${esc(b.headline)}</h2>
      ${b.benefits.length ? `<ul class="perk-list">${b.benefits.map((x) => `<li${x.id === "first_purchase_discount" ? ' class="is-hero"' : ""}><span class="perk-ico">${ICONS[x.id] || ICONS._}</span><div><strong>${esc(x.title)}</strong><span>${esc(x.description)}</span></div></li>`).join("")}</ul>` : ""}
      ${b.fine_print ? `<p class="fine">${esc(b.fine_print)}</p>` : ""}`;
  }

  /* ---------- peças do formulário ---------- */
  const field = (o) => `<div class="field"><label for="${o.id}">${o.label}</label>${o.pw
    ? `<div class="pw"><input id="${o.id}" name="${o.name}" type="password" autocomplete="${o.ac}" ${o.attrs || ""}><button class="pw-toggle" type="button" aria-label="Mostrar a senha" aria-pressed="false">${EYE}</button></div>`
    : `<input id="${o.id}" name="${o.name}" type="${o.type || "text"}" autocomplete="${o.ac || "off"}" ${o.attrs || ""}>`}${o.hint ? `<small class="hint">${o.hint}</small>` : ""}<small class="err" hidden></small></div>`;
  const submit = (label) => `<p class="form-error" role="alert" hidden></p><button class="btn btn-primary btn-block" type="submit">${label}</button>`;
  const reasonLine = () => state.reason ? `<p class="auth-reason">${esc(state.reason)}</p>` : "";

  function tabs() {
    return `<div class="seg" role="group" aria-label="Entrar ou criar conta">
      <button type="button" data-view="entrar" aria-pressed="${state.view === "entrar"}">Entrar</button>
      <button type="button" data-view="criar" aria-pressed="${state.view === "criar"}">Criar conta</button></div>`;
  }

  function social() {
    const prov = state.benefits ? state.benefits.providers : [];
    const showOff = !window.SITE.loja || window.SITE.loja.mostrarLoginSocialSemChave !== false;
    const off = (icon, name) => `<button class="btn-social is-off" type="button" disabled aria-disabled="true">${icon}<span>Continuar com ${name}</span><small>em breve</small></button>`;
    const parts = [];
    if (prov.includes("google")) parts.push('<div class="social-g" id="g-btn"></div>'); else if (showOff) parts.push(off(GOOGLE, "Google"));
    if (prov.includes("facebook")) parts.push(`<button class="btn-social" id="fb-btn" type="button">${FACEBOOK}<span>Continuar com Facebook</span></button>`); else if (showOff) parts.push(off(FACEBOOK, "Facebook"));
    return parts.length ? `<div class="social">${parts.join("")}</div><div class="or"><span>ou use e-mail ou telefone</span></div>` : "";
  }

  /* ---------- telas ---------- */
  const VIEWS = {
    entrar: () => `${reasonLine()}${tabs()}${social()}
      <form class="form" id="f-entrar" novalidate>
        ${field({ id: "a-id", name: "identifier", label: "E-mail ou telefone", ac: "username", attrs: "required" })}
        ${field({ id: "a-pw", name: "password", label: "Senha", ac: "current-password", pw: true, attrs: "required" })}
        ${submit("Entrar")}
      </form>
      <p class="alt">Esqueceu a senha ou prefere não usar uma? <button class="link-btn" type="button" data-view="codigo">Receber um código</button></p>`,

    criar: () => `${reasonLine()}${tabs()}${social()}
      <form class="form" id="f-criar" novalidate>
        ${field({ id: "c-nome", name: "name", label: "Seu nome", ac: "name", attrs: "required" })}
        ${field({ id: "c-email", name: "email", label: "E-mail", type: "email", ac: "email" })}
        ${field({ id: "c-tel", name: "phone", label: "Celular com DDD", type: "tel", ac: "tel", attrs: 'inputmode="tel" placeholder="(11) 98765-4321"', hint: "Informe o e-mail, o celular ou os dois." })}
        ${field({ id: "c-pw", name: "password", label: "Crie uma senha", ac: "new-password", pw: true, attrs: 'minlength="8" required', hint: "Mínimo de 8 caracteres." })}
        ${submit("Criar minha conta")}
      </form>`,

    codigo: () => {
      const ch = state.channel, isMail = ch === "email";
      return `${reasonLine()}<button class="back" type="button" data-view="entrar">← Voltar</button>
        <h3 class="auth-h">Entrar com um código</h3>
        <p class="auth-p">Enviamos um código de 6 dígitos. Se você ainda não tem conta, ela é criada na hora.</p>
        <div class="seg" role="group" aria-label="Onde receber o código">
          <button type="button" data-channel="email" aria-pressed="${ch === "email"}">E-mail</button>
          <button type="button" data-channel="sms" aria-pressed="${ch === "sms"}">SMS</button>
          <button type="button" data-channel="whatsapp" aria-pressed="${ch === "whatsapp"}">WhatsApp</button></div>
        <form class="form" id="f-codigo" novalidate>
          ${field({ id: "o-dest", name: "destination", label: isMail ? "Seu e-mail" : "Seu celular com DDD", type: isMail ? "email" : "tel", ac: isMail ? "email" : "tel", attrs: `required ${isMail ? "" : 'inputmode="tel" placeholder="(11) 98765-4321"'}` })}
          ${submit("Enviar código")}
        </form>`;
    },

    digitar: () => {
      const o = state.otp;
      return `<button class="back" type="button" data-view="codigo">← Trocar contato</button>
        <h3 class="auth-h">Digite o código</h3>
        <p class="auth-p">Enviamos para <strong>${esc(o.destination)}</strong>. Vale por ${Math.round((o.expires_in || 600) / 60)} minutos.</p>
        ${o.dev_code ? `<p class="dev-box">Modo de teste: seu código é <strong>${esc(o.dev_code)}</strong> <button class="link-btn" type="button" data-fill="${esc(o.dev_code)}">Preencher</button></p>` : ""}
        <form class="form" id="f-digitar" novalidate>
          ${field({ id: "d-code", name: "code", label: "Código de 6 dígitos", ac: "one-time-code", attrs: 'inputmode="numeric" maxlength="6" pattern="[0-9]*" required class="code-input"' })}
          ${field({ id: "d-nome", name: "name", label: "Como podemos te chamar? (só na primeira vez)", ac: "name" })}
          ${submit("Confirmar")}
        </form>
        <p class="alt"><button class="link-btn" type="button" id="resend" disabled>Enviar de novo</button> <span id="resend-t"></span></p>`;
    }
  };

  function render(focus) {
    main.innerHTML = VIEWS[state.view]();
    main.scrollTop = 0;
    if (focus !== false) { const f = $("input:not([type=hidden])", main); if (f && !matchMedia("(pointer: coarse)").matches) f.focus({ preventScroll: true }); }
    if (state.view === "entrar" || state.view === "criar") { mountGoogle(); preloadFacebook(); }
    if (state.view === "digitar") countdown(state.otp.cooldownEnds);
  }

  /* ---------- erros ---------- */
  function clearErrors(form) {
    $$(".field", form).forEach((f) => { f.classList.remove("has-error"); const s = $(".err", f); if (s) { s.hidden = true; s.textContent = ""; } });
    const fe = $(".form-error", form); if (fe) { fe.hidden = true; fe.textContent = ""; }
  }
  function showError(form, e) {
    const fe = $(".form-error", form); let first = null, general = e.message;
    if (e.fields) {
      general = "";
      Object.keys(e.fields).forEach((k) => {
        const input = $(`[name="${k.split(".").pop()}"]`, form);
        if (!input) { general = general || e.fields[k]; return; }
        const f = input.closest(".field"), s = $(".err", f);
        f.classList.add("has-error"); s.textContent = e.fields[k]; s.hidden = false; first = first || input;
      });
    }
    if (general && fe) { fe.textContent = general; fe.hidden = false; }
    if (first) first.focus();
  }
  async function run(form, fn) {
    clearErrors(form);
    const btn = $("button[type=submit]", form), label = btn.textContent;
    btn.disabled = true; btn.classList.add("is-busy"); btn.textContent = "Aguarde…";
    try { await fn(); } catch (e) { showError(form, e instanceof api.ApiError ? e : { message: "Algo deu errado. Tente de novo." }); if (!(e instanceof api.ApiError)) console.error(e); }
    finally { btn.disabled = false; btn.classList.remove("is-busy"); btn.textContent = label; }
  }

  /* ---------- depois de entrar ---------- */
  async function done(t) {
    await Loja.loadCart(true); /* a primeira chamada logada, com o X-Cart-Id junto, mescla o carrinho de visitante */
    dlg.close();
    const d = t.first_purchase_discount;
    if (d && d.status === "eligible" && t.is_new_user) toast(`Conta criada! Seu desconto de ${Loja.pct(d.percent)}% na primeira compra já vale no carrinho.`);
    else if (d && d.status === "eligible" && Loja.S.cart.items.length) toast(`Você entrou. O desconto de ${Loja.pct(d.percent)}% da primeira compra está no seu carrinho.`);
    else toast("Você entrou na sua conta.");
  }

  /* ---------- Google e Facebook ---------- */
  let googleStarted = false, fbStarted = null;
  async function mountGoogle() {
    const box = $("#g-btn"), id = state.config && state.config.login && state.config.login.google_client_id;
    if (!box || !id) return;
    try { await loadScript("https://accounts.google.com/gsi/client"); }
    catch (e) { box.innerHTML = '<button class="btn-social is-off" type="button" disabled>' + GOOGLE + "<span>Google indisponível agora</span></button>"; return; }
    if (!googleStarted) { window.google.accounts.id.initialize({ client_id: id, callback: (r) => socialLogin("google", r.credential), ux_mode: "popup" }); googleStarted = true; }
    if (!box.isConnected) return;
    window.google.accounts.id.renderButton(box, { type: "standard", theme: "outline", size: "large", shape: "pill", text: "continue_with", locale: "pt-BR", logo_alignment: "center",
      width: Math.max(200, Math.min(400, Math.round(box.getBoundingClientRect().width) || 320)) });
  }
  function preloadFacebook() {
    const id = state.config && state.config.login && state.config.login.facebook_app_id;
    if (!id || !$("#fb-btn") || fbStarted) return;
    fbStarted = loadScript("https://connect.facebook.net/pt_BR/sdk.js").then(() => window.FB.init({ appId: id, cookie: false, xfbml: false, version: "v21.0" }))
      .catch(() => { fbStarted = null; });
  }
  async function socialLogin(kind, token) {
    const form = $(".form", main);
    try { await done(kind === "google" ? await api.google(token) : await api.facebook(token)); }
    catch (e) { if (form) showError(form, e instanceof api.ApiError ? e : { message: "Não foi possível entrar agora. Tente de novo." }); else toast(Loja.errMsg(e)); }
  }

  /* ---------- reenvio do código ---------- */
  let timer = null;
  function countdown(endsAt) {
    clearInterval(timer);
    const btn = $("#resend"), lbl = $("#resend-t"); if (!btn) return;
    const tick = () => {
      const left = Math.max(0, Math.ceil((endsAt - Date.now()) / 1000));
      btn.disabled = left > 0; lbl.textContent = left > 0 ? `(disponível em ${left}s)` : "";
      if (!left) clearInterval(timer);
    };
    tick(); timer = setInterval(tick, 500);
  }
  async function requestCode(dest) {
    const r = await api.otpRequest(dest, state.channel);
    state.otp = { destination: dest, channel: state.channel, expires_in: r.expires_in, dev_code: r.dev_code || "", cooldownEnds: Date.now() + 60000 };
    state.view = "digitar"; render();
  }

  /* ---------- eventos ---------- */
  main.addEventListener("click", (e) => {
    const v = e.target.closest("[data-view]"); if (v) { clearInterval(timer); state.view = v.dataset.view; render(); return; }
    const ch = e.target.closest("[data-channel]"); if (ch) { state.channel = ch.dataset.channel; render(); return; }
    const fill = e.target.closest("[data-fill]"); if (fill) { $("#d-code").value = fill.dataset.fill; $("#d-code").focus(); return; }
    const pw = e.target.closest(".pw-toggle");
    if (pw) { const i = $("input", pw.parentElement), show = i.type === "password"; i.type = show ? "text" : "password"; pw.setAttribute("aria-pressed", String(show)); pw.setAttribute("aria-label", show ? "Esconder a senha" : "Mostrar a senha"); return; }
    if (e.target.closest("#fb-btn")) {
      if (!window.FB) { toast("Carregando o Facebook. Tente de novo em instantes."); preloadFacebook(); return; }
      window.FB.login((r) => { if (r && r.authResponse) socialLogin("facebook", r.authResponse.accessToken); }, { scope: "email,public_profile" });
      return;
    }
    if (e.target.closest("#resend")) {
      const o = state.otp, form = $("#f-digitar"); clearErrors(form);
      api.otpRequest(o.destination, o.channel)
        .then((r) => { state.otp = Object.assign(o, { dev_code: r.dev_code || "", cooldownEnds: Date.now() + 60000 }); render(false); toast("Enviamos um novo código."); })
        .catch((err) => showError(form, err));
    }
  });

  main.addEventListener("submit", (e) => {
    e.preventDefault();
    const form = e.target, val = (n) => form.elements[n].value.trim();
    if (form.id === "f-entrar") {
      run(form, async () => {
        if (!val("identifier") || !form.elements.password.value) throw new api.ApiError(0, "validation", "Informe seu e-mail ou telefone e a senha.");
        await done(await api.login(val("identifier"), form.elements.password.value));
      });
    } else if (form.id === "f-criar") {
      run(form, async () => {
        const f = {};
        if (val("name").length < 2) f.name = "Informe seu nome.";
        if (!val("email") && !val("phone")) f.email = "Informe o e-mail ou o celular.";
        if (form.elements.password.value.length < 8) f.password = "A senha precisa ter pelo menos 8 caracteres.";
        if (Object.keys(f).length) throw new api.ApiError(0, "validation", "Confira os campos.", f);
        const body = { name: val("name"), password: form.elements.password.value };
        if (val("email")) body.email = val("email");
        if (val("phone")) body.phone = val("phone");
        await done(await api.register(body));
      });
    } else if (form.id === "f-codigo") {
      run(form, async () => {
        if (!val("destination")) throw new api.ApiError(0, "validation", "Confira o campo.", { destination: state.channel === "email" ? "Informe seu e-mail." : "Informe seu celular com DDD." });
        await requestCode(val("destination"));
      });
    } else if (form.id === "f-digitar") {
      run(form, async () => {
        if (!/^\d{6}$/.test(val("code"))) throw new api.ApiError(0, "validation", "Confira o campo.", { code: "O código tem 6 dígitos." });
        await done(await api.otpVerify(state.otp.destination, val("code"), val("name")));
      });
    }
  });
  main.addEventListener("input", (e) => { if (e.target.name === "code") e.target.value = e.target.value.replace(/\D/g, "").slice(0, 6); });

  dlg.addEventListener("close", () => {
    clearInterval(timer);
    if (state.resolve) { const r = state.resolve; state.resolve = null; r(api.user()); }
  });

  /* ---------- abrir ---------- */
  const withTimeout = (p, ms) => Promise.race([p, new Promise((_, no) => setTimeout(() => no(new Error("timeout")), ms))]);
  function loadInfo() {
    if (state.benefits && state.config) return Promise.resolve();
    return Promise.all([withTimeout(api.benefits(), 4000).catch(() => null), withTimeout(api.config(), 4000).catch(() => null)])
      .then(([b, c]) => { state.benefits = b || state.benefits; state.config = c || state.config; });
  }

  Loja.openAuth = function (opts) {
    opts = opts || {};
    return new Promise((resolve) => {
      if (state.resolve) state.resolve(null);
      state.resolve = resolve; state.reason = opts.reason || ""; state.view = opts.view || "entrar"; state.otp = null;
      renderPerks();
      if (state.benefits) render(); else main.innerHTML = '<p class="auth-loading" role="status">Carregando…</p>';
      Loja.showDialog(dlg);
      loadInfo().then(() => {
        if (!dlg.open) return;
        renderPerks(); render();
        if (!state.benefits) main.insertAdjacentHTML("afterbegin", '<p class="form-error" role="alert">Não foi possível falar com a loja agora. Confira sua internet e tente de novo em instantes.</p>');
      });
    });
  };
})();
