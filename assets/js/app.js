/* Criando Memórias — comportamento do site (JS puro, sem build). */
(function () {
  "use strict";
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
  const html = document.documentElement;
  const SITE = window.SITE, PRODS = window.PRODUTOS, TIPOS = window.TIPOS;
  const store = {
    get(k) { try { return sessionStorage.getItem(k); } catch (e) { return null; } },
    set(k, v) { try { sessionStorage.setItem(k, v); } catch (e) { /* sem armazenamento: ok */ } }
  };
  const brl = (n) => n.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
  const norm = (s) => s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
  const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  let uid = 0;
  const cover = (p, align) => window.coverSVG(p, ++uid, align);
  const tipoRotulo = (p) => TIPOS[p.tipo].rotulo;
  const grupoTipo = (p) => TIPOS[p.tipo].grupo;
  const prefersReduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const canHover = window.matchMedia("(hover: hover)").matches;
  const ARROW = '<svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"><path d="M5 12h14m-6-6l6 6-6 6" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>';

  const BAG_PLUS = '<svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"><path d="M6.5 8.5h11l1 11.5h-13z" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/><path d="M9 8.5V7a3 3 0 0 1 6 0v1.5M12 12.5v4M10 14.5h4" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>';
  const BAG_CHECK = '<svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"><path d="M6.5 8.5h11l1 11.5h-13z" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/><path d="M9 8.5V7a3 3 0 0 1 6 0v1.5M9.6 14.4l1.8 1.8 3-3.4" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>';
  const shopOn = !SITE.loja || SITE.loja.ativa !== false;
  const HEART = '<svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"><path d="M12 20s-7.6-4.7-7.6-10.4A4.2 4.2 0 0 1 12 7.4a4.2 4.2 0 0 1 7.6 2.2C19.6 15.3 12 20 12 20z" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/></svg>';
  /* ícones das abas de ocasião (traço fino, na mesma linguagem do cabeçalho) */
  const I = (d) => `<svg viewBox="0 0 24 24" width="24" height="24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">${d}</svg>`;
  const OCC_ICON = {
    "": I('<rect x="4" y="4" width="6.5" height="6.5" rx="1.7"/><rect x="13.5" y="4" width="6.5" height="6.5" rx="1.7"/><rect x="4" y="13.5" width="6.5" height="6.5" rx="1.7"/><rect x="13.5" y="13.5" width="6.5" height="6.5" rx="1.7"/>'),
    "Festa infantil": I('<path d="M12 3.4c-3.5 0-5.8 2.8-5.8 6 0 3.5 2.7 6.2 5.8 6.2s5.8-2.7 5.8-6.2c0-3.2-2.3-6-5.8-6z"/><path d="M12 15.6l-1.3 1.7h2.6z"/><path d="M12 17.3c-1.2 1.3 1 2.5 0 3.9"/><path d="M9 7.6c.5-1 1.3-1.7 2.4-1.9"/>'),
    "Chá de bebê": I('<path d="M9.2 10.4h5.6v8.9a1.7 1.7 0 0 1-1.7 1.7h-2.2a1.7 1.7 0 0 1-1.7-1.7z"/><path d="M10 10.4V9c0-1.2.8-2 2-2s2 .8 2 2v1.4"/><path d="M12 7V4.3M10.4 4.3h3.2"/><path d="M9.2 14h2.2M9.2 17h2.2"/>'),
    "Festa adulto": I('<path d="M12 5.4l-5.6 14h11.2z"/><path d="M8.5 14.6l7 2.4M10.2 10.2l5.4 1.9"/><circle cx="12" cy="4.2" r="1.1"/><path d="M18.6 5.6v2.2M17.5 6.7h2.2M5.4 6.4v1.8M4.5 7.3h1.8"/>'),
    "Datas comemorativas": I('<rect x="4.2" y="5.6" width="15.6" height="14.2" rx="2.6"/><path d="M4.2 10h15.6M8.4 3.8v3.4M15.6 3.8v3.4"/><path d="M8.2 13.4h.01M12 13.4h.01M15.8 13.4h.01M8.2 16.5h.01M12 16.5h.01M15.8 16.5h.01" stroke-width="2"/>')
  };
  /* preferências deste navegador (favoritos e modo de exibição); sem armazenamento, o site funciona do mesmo jeito */
  const pref = {
    get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* ok */ } }
  };
  const favs = new Set((() => { try { const a = JSON.parse(pref.get("cm-favoritos") || "[]"); return Array.isArray(a) ? a.filter(Number.isInteger) : []; } catch (e) { return []; } })());

  html.classList.add("js");
  if (!shopOn) html.classList.add("sem-loja");
  $("#ano").textContent = new Date().getFullYear();

  /* ---------- Barra promocional ---------- */
  (function promo() {
    const el = $("#promo"), cfg = SITE.promo;
    if (!cfg || !cfg.ativa || store.get("cm-promo") === "off") { el.hidden = true; return; }
    const grupo = (hidden) => `<div class="promo-group"${hidden ? ' aria-hidden="true"' : ""}>${cfg.mensagens.map((m) => `<span>${esc(m)}</span>`).join("")}</div>`;
    $("#promo-track").innerHTML = grupo(false) + grupo(true);
    const a = $("#promo-link"); a.textContent = cfg.link.texto; a.href = cfg.link.href;
    $("#promo-close").addEventListener("click", () => { el.hidden = true; store.set("cm-promo", "off"); });
  })();

  /* ---------- Abertura em vídeo (com música) ---------- */
  (function splash() {
    const el = $("#splash"), v = $("#splash-video"), skip = $("#splash-skip"), snd = $("#splash-sound");
    if (!html.classList.contains("splash-on")) return;
    const cfg = SITE.abertura;
    if (!cfg || !cfg.ativa) { html.classList.remove("splash-on"); return; }
    const wantSound = cfg.som !== false;

    /* Qual arquivo: 4K (HEVC) só em tela grande e nítida, sem toque e sem economia de dados, e só onde o navegador toca HEVC;
       1080 para o resto; 720 para tela pequena ou conexão lenta. Se nada disso se aplica, valem os <source> do HTML. */
    (function pick() {
      const conn = navigator.connection || {};
      const slow = !!conn.saveData || /(^|-)(2g|3g)$/.test(conn.effectiveType || "");
      const px = window.innerWidth * (window.devicePixelRatio || 1), touch = matchMedia("(pointer: coarse)").matches;
      const can = (type) => !!v.canPlayType(type);
      let src = "";
      if (!slow && !touch && px >= 2400 && can('video/mp4; codecs="hvc1.1.6.L153.B0"')) src = "assets/video/abertura-4k.mp4";
      else if (can('video/mp4; codecs="avc1.640028"')) src = slow || px < 1000 ? "assets/video/abertura-720.mp4" : "assets/video/abertura-1080.mp4";
      if (src) { v.src = src; v.load(); }
      v.dataset.fonte = v.dataset.escolhido = src || "html";
    })();

    let done = false, started = false;
    const fadeOut = (ms) => { /* a música some junto com a dissolução da tela */
      if (v.muted) return;
      const t0 = performance.now(), v0 = v.volume;
      (function step() { const k = Math.min(1, (performance.now() - t0) / ms); try { v.volume = v0 * (1 - k); } catch (e) { /* iOS: volume só leitura */ } if (k < 1) requestAnimationFrame(step); })();
    };
    const end = () => {
      if (done) return; done = true;
      store.set("cm-abertura", "1");
      el.classList.add("is-out"); fadeOut(600);
      setTimeout(() => { html.classList.remove("splash-on"); try { v.pause(); } catch (e) { /* ok */ } }, 700);
    };

    /* botão de som */
    const paintSound = () => {
      const on = !v.muted && v.volume > 0;
      snd.classList.toggle("is-on", on); snd.setAttribute("aria-pressed", String(on));
      $(".snd-txt", snd).textContent = on ? "Som ligado" : "Ativar som";
    };
    snd.hidden = !wantSound;
    snd.addEventListener("click", () => { v.muted = !v.muted; if (!v.muted && v.volume === 0) v.volume = .9; paintSound(); });
    v.addEventListener("volumechange", paintSound);

    /* rede de segurança: se o navegador disse que toca o 4K (HEVC) mas não mostra imagem, troca para o 1080 sem travar */
    const fallback4k = () => {
      if (!/4k/.test(v.dataset.fonte)) return false;
      v.dataset.fonte = "assets/video/abertura-1080.mp4"; v.src = v.dataset.fonte; v.load();
      const q = v.play(); if (q && q.catch) q.catch(() => { /* já tratado pelo tempo limite */ });
      return true;
    };

    skip.addEventListener("click", end);
    document.addEventListener("keydown", (e) => { if (e.key === "Escape") end(); });
    v.addEventListener("ended", end);
    v.addEventListener("error", () => { if (!fallback4k()) setTimeout(end, 600); });
    v.addEventListener("loadeddata", () => { if (v.videoWidth === 0) fallback4k(); });
    v.addEventListener("playing", () => { started = true; });
    v.addEventListener("timeupdate", () => { if (v.currentTime >= cfg.fadeEmSegundos) end(); });

    /* tenta com som; se o navegador bloquear (quase sempre na primeira visita), toca mudo e o botão "Ativar som" fica à espera */
    if (wantSound) { v.muted = false; v.volume = .9; }
    paintSound();
    const p = v.play();
    if (p && p.catch) p.catch(() => {
      v.muted = true; paintSound();
      const q = v.play(); if (q && q.catch) q.catch(() => setTimeout(end, 1800));
    });
    setTimeout(() => { if (!started) end(); }, 8000);  /* não travou o carregamento: se não começou em 8 s, segue para o site */
    setTimeout(end, 15000);
  })();

  /* ---------- Cabeçalho ---------- */
  const header = $(".site-header"), btnMenu = $("#btn-menu");
  const setMenu = (open) => { header.classList.toggle("nav-open", open); btnMenu.setAttribute("aria-expanded", String(open)); };
  btnMenu.addEventListener("click", () => setMenu(!header.classList.contains("nav-open")));
  $$("#nav a").forEach((a) => a.addEventListener("click", () => setMenu(false)));
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") setMenu(false); });
  $("#btn-busca").addEventListener("click", () => {
    $("#catalogo").scrollIntoView({ behavior: prefersReduced ? "auto" : "smooth" });
    setTimeout(() => $("#q").focus({ preventScroll: true }), prefersReduced ? 0 : 450);
  });
  (function headerMotion() {
    const onScroll = () => header.classList.toggle("is-scrolled", window.scrollY > 24);
    window.addEventListener("scroll", onScroll, { passive: true }); onScroll();
    /* destaca no menu a seção que está no meio da tela */
    const map = { inicio: "#ocasioes", ocasioes: "#ocasioes", destaques: "#catalogo", catalogo: "#catalogo" };
    const links = $$("#nav a");
    if (!("IntersectionObserver" in window)) return;
    const io = new IntersectionObserver((es) => es.forEach((e) => {
      if (e.isIntersecting) links.forEach((a) => a.classList.toggle("is-active", !!map[e.target.id] && a.getAttribute("href") === map[e.target.id]));
    }), { rootMargin: "-45% 0px -50% 0px" });
    $$("main > section").forEach((s) => io.observe(s));
  })();

  /* ---------- Fundo ambiente: as formas se movem de leve com a rolagem ---------- */
  (function parallax() {
    const els = $$(".amb[data-speed]");
    if (prefersReduced || !els.length) return;
    let busy = false;
    const upd = () => { const y = window.scrollY; els.forEach((el) => { el.style.translate = `0 ${(y * parseFloat(el.dataset.speed)).toFixed(1)}px`; }); busy = false; };
    window.addEventListener("scroll", () => { if (!busy) { busy = true; requestAnimationFrame(upd); } }, { passive: true });
  })();

  /* ---------- Atendimento (WhatsApp) ---------- */
  let toastTimer;
  function toast(msg) {
    const t = $("#toast"); t.textContent = msg; t.hidden = false;
    try { if (t.showPopover) { if (t.matches(":popover-open")) t.hidePopover(); t.showPopover(); } } catch (e) { /* sem popover: fica no fluxo normal */ }
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { t.hidden = true; try { if (t.hidePopover && t.matches(":popover-open")) t.hidePopover(); } catch (e) { /* ok */ } }, 4600);
  }
  /* uma janela aberta depois do aviso fica por cima dele: puxa o aviso de volta para a frente */
  function raiseToast() {
    const t = $("#toast");
    try { if (!t.hidden && t.matches(":popover-open")) { t.hidePopover(); t.showPopover(); } } catch (e) { /* ok */ }
  }
  function consultar(nome) {
    const msg = nome ? `Oi! Tenho interesse no kit "${nome}". Pode me explicar como funciona?` : "Oi! Quero conhecer os kits digitais da Criando Memórias.";
    const num = String(SITE.whatsapp || "").replace(/\D/g, "");
    if (num) { window.open(`https://wa.me/${num}?text=${encodeURIComponent(msg)}`, "_blank", "noopener"); return; }
    if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(msg).catch(() => {});
    toast("O canal de atendimento ainda está em configuração. A mensagem foi copiada.");
  }
  $$("[data-consultar]").forEach((b) => b.addEventListener("click", () => consultar("")));

  /* ---------- Cartões ----------
     o.anim = ordem de entrada ao filtrar */
  function cardHTML(p, o = {}) {
    const anim = o.anim != null ? ` card-in" style="--i:${Math.min(o.anim, 11)}` : "";
    const fav = favs.has(p.id);
    const card = `<article class="card${anim}">
      <div class="card-cover">${cover(p)}<span class="tag">${esc(tipoRotulo(p))}</span>
        <button class="fav" type="button" data-fav="${p.id}" aria-pressed="${fav}" aria-label="${fav ? "Remover dos favoritos" : "Favoritar"}: ${esc(p.nome)}">${HEART}</button>
        ${shopOn ? `<button class="card-add" type="button" data-add="${p.id}" aria-pressed="false" aria-label="Adicionar ${esc(p.nome)} ao carrinho" title="Adicionar ao carrinho"><span class="ico-add">${BAG_PLUS}</span><span class="ico-in">${BAG_CHECK}</span></button>` : ""}</div>
      <div class="card-body"><h3>${esc(p.nome)}</h3><p class="card-meta">${esc(p.ocasiao)}</p>
        <div class="card-foot"><p class="card-price">${brl(p.preco)}</p><button class="card-btn" type="button" data-id="${p.id}" aria-label="Ver o kit ${esc(p.nome)}"><span class="lbl">Ver kit</span>${ARROW}</button></div></div>
    </article>`;
    return card;
  }
  function toggleFav(id) {
    const p = PRODS.find((x) => x.id === id); if (!p) return;
    const on = !favs.has(id); on ? favs.add(id) : favs.delete(id);
    pref.set("cm-favoritos", JSON.stringify(Array.from(favs)));
    $$(`[data-fav="${id}"]`).forEach((b) => {
      b.setAttribute("aria-pressed", String(on)); b.setAttribute("aria-label", `${on ? "Remover dos favoritos" : "Favoritar"}: ${p.nome}`);
      if (on && !prefersReduced) { b.classList.remove("pop"); void b.offsetWidth; b.classList.add("pop"); }
    });
    if (on && !store.get("cm-dica-fav")) { store.set("cm-dica-fav", "1"); toast("Salvo nos favoritos. Para ver só eles, abra Filtros."); }
    const n = $("#fav-n"); if (n) n.textContent = favs.size;
    if (state.fav.size) render(Infinity); /* vendo só os favoritos: o cartão desfavoritado sai da lista */
  }
  const onCardClick = (e) => { const f = e.target.closest("[data-fav]"); if (f) { toggleFav(Number(f.dataset.fav)); return; } openFromClick(e); };
  const openFromClick = (e) => { const b = e.target.closest("[data-id]"); if (b) openProduct(Number(b.dataset.id)); };

  /* ---------- Ilustração do início: entra pronta e as camadas se movem de leve com o mouse ---------- */
  (function hero() {
    const art = $("#hero-art"); if (!art || !window.heroSVG) return;
    art.innerHTML = window.heroSVG();
    if (prefersReduced || !canHover) return;
    const layers = $$("[data-depth]", art).map((g) => ({ g, d: parseFloat(g.dataset.depth) }));
    const area = $("#inicio"); let raf = 0, tx = 0, ty = 0;
    const apply = () => { raf = 0; layers.forEach(({ g, d }) => { g.style.translate = `${(tx * d * 22).toFixed(1)}px ${(ty * d * 16).toFixed(1)}px`; }); };
    area.addEventListener("pointermove", (e) => {
      const r = art.getBoundingClientRect();
      tx = Math.max(-1, Math.min(1, (e.clientX - (r.left + r.width / 2)) / r.width)); ty = Math.max(-1, Math.min(1, (e.clientY - (r.top + r.height / 2)) / r.height));
      if (!raf) raf = requestAnimationFrame(apply);
    });
    area.addEventListener("pointerleave", () => { tx = ty = 0; apply(); });
  })();

  /* ---------- Ocasiões e destaques ---------- */
  const OCC_ORDER = ["Festa infantil", "Chá de bebê", "Festa adulto", "Datas comemorativas"];
  /* motivo e cores de cada cartão de ocasião: bg = degradê do cartão · disc = cor do círculo do desenho · pal = cores do desenho */
  const OCC = {
    "Festa infantil":      { motif: "balloons", pal: ["#8CB8D9", "#E58C9A", "#F2C94C"], bg: ["#F2F9F6", "#E3F2EC"], disc: "#D2EAE1" },
    "Chá de bebê":         { motif: "moon",     pal: ["#A9B9E3", "#F2DFB4", "#65516F"], bg: ["#F5F5FC", "#EAEDF9"], disc: "#DDE2F4" },
    "Festa adulto":        { motif: "cup",      pal: ["#EDC9C1", "#9DD2C8", "#65516F"], bg: ["#FDF3F0", "#F9E5E0"], disc: "#F5D9D3" },
    "Datas comemorativas": { motif: "sparkle",  pal: ["#B9A5C1", "#F2C94C", "#9DD2C8"], bg: ["#FEFAEE", "#FBF1D9"], disc: "#F7EAC2" }
  };
  const state = { q: "", oc: new Set(), tipo: new Set(), tema: new Set(), fav: new Set(), min: "", max: "", ordem: "destaque", todos: false, view: pref.get("cm-visao") === "lista" ? "lista" : "grade" };
  /* a grade abre com uma fileira (como na referência); "Explorar todos os kits" mostra o resto */
  const cols = () => (window.innerWidth >= 1100 ? 4 : window.innerWidth >= 700 ? 3 : 2);
  const firstPage = () => (state.view === "lista" ? 4 : cols() >= 4 ? 4 : cols() * 2);

  (function occasions() {
    const counts = {}; PRODS.forEach((p) => { counts[p.ocasiao] = (counts[p.ocasiao] || 0) + 1; });
    const list = OCC_ORDER.filter((o) => counts[o]);
    const box = $("#occasions");
    box.innerHTML = list.map((o, i) => {
      const cfg = OCC[o] || OCC["Datas comemorativas"];
      return `<div class="reveal" style="--d:${i * 90}ms"><button class="occ" type="button" data-occ="${esc(o)}" style="--bg1:${cfg.bg[0]};--bg2:${cfg.bg[1]};--disc:${cfg.disc}">
        <span class="occ-disc"><span class="occ-art">${window.motifSVG(cfg.motif, cfg.pal)}</span></span>
        <span class="occ-info"><span class="occ-title">${esc(o)}</span><span class="occ-count">${counts[o]} ${counts[o] === 1 ? "kit" : "kits"}</span></span>
        <span class="occ-go" aria-hidden="true">${ARROW}</span></button></div>`;
    }).join("");
    box.addEventListener("click", (e) => {
      const b = e.target.closest("[data-occ]"); if (!b) return;
      resetFilters(false); state.oc.add(b.dataset.occ); syncControls(); render();
      const on = $(".occ-chip[aria-pressed='true']"); if (on) on.scrollIntoView({ inline: "center", block: "nearest" });
      $("#catalogo").scrollIntoView({ behavior: prefersReduced ? "auto" : "smooth" });
    });
    const feat = PRODS.filter((p) => p.d).slice(0, 4);
    /* "Em destaque": o primeiro kit vira o cartão grande; os outros entram na lista ao lado */
    const [big, ...rest] = feat, hexA = (h, a) => { const n = parseInt(h.slice(1), 16); return `rgba(${n >> 16},${(n >> 8) & 255},${n & 255},${a})`; };
    if (big) {
      const m = $("#feat-main"), [ca, , , cbg] = big.p;
      m.style.background = `linear-gradient(104deg, ${cbg} 0%, ${cbg} 34%, ${hexA(ca, .3)} 100%) #fff`;
      m.innerHTML = `<div class="feat-art">${cover(big, "grande")}<span class="tag">${esc(tipoRotulo(big))}</span></div>
        <div class="feat-copy"><p class="feat-kicker">${esc(big.chamada || big.ocasiao)}</p><h3>${esc(big.nome)}</h3>
          <p class="feat-text">${esc(big.texto || "Kit digital para preparar a sua festa com carinho.")}</p><p class="feat-big-price">${brl(big.preco)}</p>
          <button class="btn-feat" type="button" data-id="${big.id}" aria-label="Conhecer o kit ${esc(big.nome)}">Conhecer o kit ${ARROW}</button></div>`;
    }
    $("#feat-list").innerHTML = rest.map((p) => `<article class="feat-row"><div class="feat-thumb">${cover(p, "wide")}</div>
      <div class="feat-info"><h3>${esc(p.nome)}</h3><p class="feat-price">${brl(p.preco)}</p></div>
      <button class="feat-go" type="button" data-id="${p.id}" aria-label="Ver o kit ${esc(p.nome)}">${ARROW}</button></article>`).join("");
    $("#destaques").addEventListener("click", openFromClick);
  })();

  /* ---------- Filtros ---------- */
  const count = (key) => { const m = new Map(); PRODS.forEach((p) => { const v = key(p); m.set(v, (m.get(v) || 0) + 1); }); return m; };
  const GROUPS = [ /* a ocasião fica nos botões acima da grade; aqui entram os filtros finos */
    { id: "tipo", titulo: "Tipo", get: grupoTipo },
    { id: "tema", titulo: "Tema", get: (p) => p.tema }
  ];
  function buildFilters() {
    const body = $("#filtros-body");
    const groups = GROUPS.map((g) => {
      const m = count(g.get); const keys = Array.from(m.keys()).sort((a, b) => m.get(b) - m.get(a));
      return `<div class="f-group" role="group" aria-labelledby="fg-${g.id}"><p class="f-title" id="fg-${g.id}">${g.titulo}</p><div class="f-options">${keys.map((k) =>
        `<label class="pill"><input type="checkbox" data-g="${g.id}" value="${esc(k)}"><span>${esc(k)} <small>${m.get(k)}</small></span></label>`).join("")}</div></div>`;
    }).join("");
    const prices = PRODS.map((p) => p.preco), lo = Math.floor(Math.min(...prices)), hi = Math.ceil(Math.max(...prices));
    const favGroup = `<div class="f-group" role="group" aria-labelledby="fg-fav"><p class="f-title" id="fg-fav">Favoritos</p><div class="f-options"><label class="pill"><input type="checkbox" data-g="fav" value="1"><span>Só os meus favoritos <small id="fav-n">${favs.size}</small></span></label></div></div>`;
    body.innerHTML = favGroup + groups + `<div class="f-group" role="group" aria-labelledby="fg-preco"><p class="f-title" id="fg-preco">Preço (R$)</p><div class="price-row">
      <label>Mínimo<input id="pmin" type="number" inputmode="numeric" min="0" step="1" placeholder="${lo}"></label>
      <label>Máximo<input id="pmax" type="number" inputmode="numeric" min="0" step="1" placeholder="${hi}"></label></div></div>`;
    body.addEventListener("change", (e) => {
      const i = e.target.closest("input[data-g]"); if (!i) return;
      const set = state[i.dataset.g]; i.checked ? set.add(i.value) : set.delete(i.value);
      state.todos = false; render();
    });
    let t; body.addEventListener("input", (e) => {
      if (e.target.id !== "pmin" && e.target.id !== "pmax") return;
      clearTimeout(t); t = setTimeout(() => { state.min = $("#pmin").value; state.max = $("#pmax").value; state.todos = false; render(); }, 250);
    });
  }
  function buildOccChips() {
    const counts = count((p) => p.ocasiao);
    const items = [["", "Todos", PRODS.length]].concat(OCC_ORDER.filter((o) => counts.get(o)).map((o) => [o, o, counts.get(o)]));
    const box = $("#occ-chips");
    box.innerHTML = items.map(([v, l, n]) => `<button class="occ-chip" type="button" data-v="${esc(v)}" aria-pressed="false"><span class="oc-ico">${OCC_ICON[v] || OCC_ICON[""]}</span><span>${esc(l)}</span><small>${n}</small></button>`).join("");
    box.addEventListener("click", (e) => {
      const b = e.target.closest(".occ-chip"); if (!b) return;
      const v = b.dataset.v, was = state.oc.has(v);
      state.oc.clear(); if (v && !was) state.oc.add(v);
      state.todos = false; render();
    });
  }
  function syncControls() {
    $$("#filtros-body input[data-g]").forEach((i) => { i.checked = state[i.dataset.g].has(i.value); });
    $("#pmin").value = state.min; $("#pmax").value = state.max; $("#q").value = state.q; $("#ordem").value = state.ordem;
  }
  function resetFilters(doRender = true) {
    state.q = ""; state.oc.clear(); state.tipo.clear(); state.tema.clear(); state.fav.clear(); state.min = ""; state.max = ""; state.todos = false;
    syncControls(); if (doRender) render();
  }
  function activeCount() { return state.tipo.size + state.tema.size + state.fav.size + (state.min !== "" ? 1 : 0) + (state.max !== "" ? 1 : 0); }

  function filtered() {
    const tokens = norm(state.q).split(/\s+/).filter(Boolean);
    const min = state.min === "" ? -Infinity : Number(state.min), max = state.max === "" ? Infinity : Number(state.max);
    let r = PRODS.filter((p) => {
      if (state.oc.size && !state.oc.has(p.ocasiao)) return false;
      if (state.tipo.size && !state.tipo.has(grupoTipo(p))) return false;
      if (state.tema.size && !state.tema.has(p.tema)) return false;
      if (state.fav.size && !favs.has(p.id)) return false;
      if (p.preco < min || p.preco > max) return false;
      if (tokens.length) { const hay = norm(`${p.nome} ${p.tema} ${p.ocasiao} ${tipoRotulo(p)}`); if (!tokens.every((t) => hay.includes(t))) return false; }
      return true;
    });
    const cmp = { menor: (a, b) => a.preco - b.preco || a.nome.localeCompare(b.nome, "pt-BR"), maior: (a, b) => b.preco - a.preco || a.nome.localeCompare(b.nome, "pt-BR"), az: (a, b) => a.nome.localeCompare(b.nome, "pt-BR"), za: (a, b) => b.nome.localeCompare(a.nome, "pt-BR") }[state.ordem];
    if (cmp) r = r.slice().sort(cmp);
    return r;
  }

  /* animFrom: a partir de qual cartão a animação de entrada roda (em "mostrar mais", só os novos) */
  function render(animFrom = 0) {
    const all = filtered(), shown = state.todos ? all : all.slice(0, firstPage());
    $("#grade").dataset.view = state.view;
    $("#grade").innerHTML = shown.map((p, i) => cardHTML(p, i >= animFrom && !prefersReduced ? { anim: i - animFrom } : {})).join("");
    $("#vazio").hidden = all.length > 0;
    $("#grade").hidden = all.length === 0;
    $("#contagem").textContent = `${all.length} ${all.length === 1 ? "kit encontrado" : "kits encontrados"}`;
    const more = shown.length < all.length;
    $("#mais-wrap").hidden = !more;
    $("#mais-txt").textContent = state.q.trim() || state.oc.size || activeCount() ? "Ver todos os resultados" : "Explorar todos os kits";
    $("#mais-status").textContent = all.length ? `Mostrando ${shown.length} de ${all.length}` : "";
    const fn = $("#fav-n"); if (fn) fn.textContent = favs.size;
    $$(".view-toggle button").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.view === state.view)));
    $$(".occ-chip").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.v === "" ? state.oc.size === 0 : state.oc.has(b.dataset.v))));
    // chips dos filtros ativos (a ocasião já aparece nos botões acima da grade)
    const chips = [];
    const add = (label, fn) => chips.push({ label, fn });
    state.tipo.forEach((v) => add(v, () => state.tipo.delete(v)));
    state.tema.forEach((v) => add(v, () => state.tema.delete(v)));
    if (state.fav.size) add("Só favoritos", () => state.fav.clear());
    if (state.min !== "") add(`A partir de ${brl(Number(state.min))}`, () => { state.min = ""; });
    if (state.max !== "") add(`Até ${brl(Number(state.max))}`, () => { state.max = ""; });
    if (state.q.trim()) add(`Busca: ${state.q.trim()}`, () => { state.q = ""; });
    const box = $("#chips"); box.innerHTML = "";
    chips.forEach((c) => {
      const b = document.createElement("button"); b.type = "button"; b.className = "chip";
      b.innerHTML = `${esc(c.label)} <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true"><path d="M7 7l10 10M17 7L7 17" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" fill="none"/></svg>`;
      b.setAttribute("aria-label", `Remover filtro ${c.label}`);
      b.addEventListener("click", () => { c.fn(); state.todos = false; syncControls(); render(); });
      box.appendChild(b);
    });
    if (chips.length > 1) {
      const b = document.createElement("button"); b.type = "button"; b.className = "chip chip-clear"; b.textContent = "Limpar tudo";
      b.addEventListener("click", () => resetFilters()); box.appendChild(b);
    }
    const n = activeCount(); const badge = $("#filtros-badge"); badge.hidden = n === 0; badge.textContent = n;
    $("#filtros-aplicar").textContent = `Ver ${all.length} ${all.length === 1 ? "kit" : "kits"}`;
    document.dispatchEvent(new Event("cm:cards"));
  }

  buildFilters();
  buildOccChips();
  $("#grade").addEventListener("click", onCardClick);
  $("#mais").addEventListener("click", () => { state.todos = true; const before = $$("#grade .card").length; render(before); const nx = $$("#grade .card")[before]; if (nx) nx.querySelector(".card-btn").focus({ preventScroll: true }); });
  let qt; $("#q").addEventListener("input", (e) => { clearTimeout(qt); qt = setTimeout(() => { state.q = e.target.value; state.todos = false; render(); }, 160); });
  $("#ordem").addEventListener("change", (e) => { state.ordem = e.target.value; state.todos = false; render(); });
  $$(".view-toggle button").forEach((b) => b.addEventListener("click", () => {
    if (state.view === b.dataset.view) return;
    state.view = b.dataset.view; pref.set("cm-visao", state.view); render(Infinity);
  }));
  let rz, lastFirst = firstPage(); /* ao girar o aparelho ou mudar a janela, a primeira fileira acompanha as colunas */
  window.addEventListener("resize", () => { clearTimeout(rz); rz = setTimeout(() => { const f = firstPage(); if (f !== lastFirst) { lastFirst = f; if (!state.todos) render(Infinity); } }, 160); });
  $("#filtros-limpar").addEventListener("click", () => resetFilters());
  $("#vazio-limpar").addEventListener("click", () => resetFilters());

  /* Painel de filtros (gaveta lateral) */
  const drawer = $("#filtros"), backdrop = $("#backdrop"), openBtn = $("#filtros-abrir");
  /* a rolagem da página só volta quando nenhuma janela nem a gaveta de filtros estiver aberta */
  const syncScroll = () => { document.body.style.overflow = ($("dialog[open]") || drawer.classList.contains("open")) ? "hidden" : ""; };
  const setDrawer = (open) => {
    drawer.classList.toggle("open", open); backdrop.hidden = !open; openBtn.setAttribute("aria-expanded", String(open));
    document.body.style.overflow = open ? "hidden" : "";
    if (open) { const f = $("input", drawer); if (f) f.focus({ preventScroll: true }); } else if (document.activeElement && drawer.contains(document.activeElement)) openBtn.focus({ preventScroll: true });
  };
  openBtn.addEventListener("click", () => setDrawer(true));
  $("#filtros-fechar").addEventListener("click", () => setDrawer(false));
  $("#filtros-aplicar").addEventListener("click", () => setDrawer(false));
  backdrop.addEventListener("click", () => setDrawer(false));
  document.addEventListener("keydown", (e) => { if (e.key === "Escape" && drawer.classList.contains("open")) setDrawer(false); });

  /* ---------- Página do produto ---------- */
  const dlg = $("#produto");
  const SPEC = ["Conteúdo do kit", "Arquivos e formatos", "Tamanhos", "Edição", "Personalização", "Entrega", "Uso e suporte"];
  let current = null, lastFocus = null;
  function openProduct(id, fromHash) {
    const p = PRODS.find((x) => x.id === id); if (!p) return;
    current = p; lastFocus = document.activeElement;
    $("#p-capa").innerHTML = cover(p);
    $("#p-ocasiao").textContent = p.tema === "Outros temas" ? p.ocasiao : `${p.ocasiao} · ${p.tema}`;
    $("#p-nome").textContent = p.nome;
    $("#p-tipo").textContent = tipoRotulo(p);
    $("#p-preco").textContent = brl(p.preco);
    $("#p-spec").innerHTML = SPEC.map((s) => `<div><dt>${s}</dt><dd>A confirmar com o catálogo real</dd></div>`).join("");
    if (!dlg.open) dlg.showModal();
    $(".product-in", dlg).scrollTop = 0; $(".product-info", dlg).scrollTop = 0;
    document.body.style.overflow = "hidden";
    if (!fromHash) history.replaceState(null, "", `#kit-${p.slug}`);
    document.dispatchEvent(new CustomEvent("cm:produto", { detail: p }));
  }
  function closeProduct() { if (dlg.open) dlg.close(); }
  dlg.addEventListener("close", () => {
    syncScroll();
    if (location.hash.startsWith("#kit-")) history.replaceState(null, "", "#catalogo");
    if (lastFocus && lastFocus.focus) lastFocus.focus({ preventScroll: true });
  });
  dlg.addEventListener("click", (e) => { if (e.target === dlg) closeProduct(); });
  $("#p-fechar").addEventListener("click", closeProduct);
  $("#p-voltar").addEventListener("click", closeProduct);
  $("#p-consultar").addEventListener("click", () => consultar(current ? `${tipoRotulo(current)} · ${current.nome}` : ""));
  const fromHash = () => { const m = location.hash.match(/^#kit-(.+)$/); if (!m) return; const p = PRODS.find((x) => x.slug === m[1]); if (p) openProduct(p.id, true); };
  window.addEventListener("hashchange", () => { if (location.hash.startsWith("#kit-")) fromHash(); else closeProduct(); });

  /* ---------- Entrada suave ---------- */
  (function reveal() {
    const els = $$(".reveal");
    if (!("IntersectionObserver" in window) || prefersReduced) { els.forEach((e) => e.classList.add("in")); return; }
    const io = new IntersectionObserver((entries) => entries.forEach((en) => { if (en.isIntersecting) { en.target.classList.add("in"); io.unobserve(en.target); } }), { rootMargin: "0px 0px -8% 0px", threshold: 0.08 });
    els.forEach((e) => io.observe(e));
  })();

  /* o que as telas da loja (loja.js, entrar.js, conta.js, checkout.js) reaproveitam */
  window.CM = { $, $$, esc, brl, toast, raiseToast, cover, PRODS, prefersReduced, ARROW, BAG_PLUS, syncScroll, closeProduct, currentKit: () => current, shopOn };

  render();
  fromHash();
})();
