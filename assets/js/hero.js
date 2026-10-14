/* Criando Memórias — ilustração da abertura: cartão "Vamos celebrar" diante de um envelope, balões, ramos de flor e um pódio,
   sobre colinas de papel em menta, lavanda e rosa. Desenhada em SVG, sem imagens. Medidas tiradas da referência de layout
   (viewBox 972×560). Cada camada tem data-depth: o fundo se move de leve com o mouse (app.js). */
(function () {
  "use strict";
  const f = (n) => Math.round(n * 10) / 10;
  const rad = (a) => (a * Math.PI) / 180;
  /* aleatório com semente fixa: os ramos de flor saem sempre iguais */
  const rng = (seed) => { let s = seed >>> 0; return () => { s = (s * 1664525 + 1013904223) >>> 0; return s / 4294967296; }; };

  /* estrela de quatro pontas, centrada na origem do próprio grupo (assim o brilho pisca em torno do centro) */
  function star(cx, cy, R, fill, delay) {
    const k = f(R * 0.2);
    return `<g transform="translate(${cx} ${cy})"><path class="spark" style="--d:${delay}s" fill="${fill}" d="M0 ${-R}Q${k} ${-k} ${R} 0Q${k} ${k} 0 ${R}Q${-k} ${k} ${-R} 0Q${-k} ${-k} 0 ${-R}Z"/></g>`;
  }

  /* balão com brilho e fio; o fio sobe junto com o balão e termina escondido atrás do envelope */
  function balloon(o) {
    const { cx, cy, rx, ry, rot, id, dur, delay, end, c } = o;
    const h = ry + 6, kx = cx - h * Math.sin(rad(rot)), ky = cy + h * Math.cos(rad(rot));
    const mx = (kx + end[0]) / 2 + (o.sway || 0), my = (ky + end[1]) / 2;
    return `<g class="float" style="--dur:${dur}s;--d:${delay}s">
      <path d="M${f(kx)} ${f(ky)}Q${f(mx)} ${f(my)} ${end[0]} ${end[1]}" fill="none" stroke="#6F7468" stroke-opacity=".8" stroke-width="1.3" stroke-linecap="round"/>
      <g transform="translate(${cx} ${cy}) rotate(${rot})">
        <path d="M${f(-rx * 0.22)} ${f(ry * 0.92)}L${f(rx * 0.22)} ${f(ry * 0.92)}L${f(rx * 0.04)} ${f(ry + 8)}Z" fill="${c[2]}"/>
        <path d="M0 ${-ry}C${f(rx * 1.06)} ${-ry} ${f(rx * 1.1)} ${f(ry * 0.42)} 0 ${ry}C${f(-rx * 1.1)} ${f(ry * 0.42)} ${f(-rx * 1.06)} ${-ry} 0 ${-ry}Z" fill="url(#hr-b-${id})"/>
        <ellipse cx="${f(-rx * 0.4)}" cy="${f(-ry * 0.46)}" rx="${f(rx * 0.17)}" ry="${f(ry * 0.27)}" fill="#fff" fill-opacity=".62" transform="rotate(26 ${f(-rx * 0.4)} ${f(-ry * 0.46)})"/>
        <ellipse cx="${f(rx * 0.5)}" cy="${f(ry * 0.28)}" rx="${f(rx * 0.06)}" ry="${f(ry * 0.15)}" fill="#fff" fill-opacity=".26"/>
      </g></g>`;
  }
  const balloonGrad = (id, c) => `<radialGradient id="hr-b-${id}" cx="34%" cy="27%" r="82%"><stop offset="0" stop-color="${c[0]}"/><stop offset=".5" stop-color="${c[1]}"/><stop offset="1" stop-color="${c[2]}"/></radialGradient>`;

  /* ramo de gipsofila: haste verde-oliva que se divide e termina em cachos de flores de cinco pétalas */
  function sprig(x0, y0, ang, len, seed, tipScale) {
    const r = rng(seed); let stems = "", flowers = "";
    const flower = (x, y, s) => { flowers += `<use href="#hr-fl" transform="translate(${f(x)} ${f(y)}) rotate(${f(r() * 72)}) scale(${f(s)})"/>`; };
    function cluster(x, y) {
      const n = 4 + ((r() * 3) | 0);
      for (let i = 0; i < n; i++) {
        const a = r() * Math.PI * 2, d = Math.sqrt(r()) * 12 * tipScale;
        flower(x + Math.cos(a) * d, y + Math.sin(a) * d, (0.95 + r() * 0.7) * tipScale);
      }
      for (let i = 0; i < 2; i++) { const a = r() * 6.28, d = 6 + r() * 12 * tipScale; flowers += `<circle cx="${f(x + Math.cos(a) * d)}" cy="${f(y + Math.sin(a) * d)}" r="${f(1.2 + r() * 1.1)}" fill="#F4EEDC"/>`; }
    }
    function branch(x, y, a, l, depth) {
      const a1 = a + (r() - 0.5) * 34, x1 = x + Math.cos(rad(a1)) * l, y1 = y + Math.sin(rad(a1)) * l;
      const qx = x + Math.cos(rad(a)) * l * 0.62, qy = y + Math.sin(rad(a)) * l * 0.62;
      stems += `<path d="M${f(x)} ${f(y)}Q${f(qx)} ${f(qy)} ${f(x1)} ${f(y1)}" stroke-width="${f(1.1 + depth * 0.4)}"/>`;
      if (depth === 0) { cluster(x1, y1); return; }
      const n = depth > 1 ? 3 : 2;
      for (let i = 0; i < n; i++) {
        const t = 0.32 + (i / n) * 0.62, px = x + (x1 - x) * t, py = y + (y1 - y) * t;
        branch(px, py, a1 + (i % 2 ? 1 : -1) * (20 + r() * 26), l * (0.5 + r() * 0.2), depth - 1);
      }
      branch(x1, y1, a1 + (r() - 0.5) * 24, l * 0.42, 0);
    }
    branch(x0, y0, ang, len, 2);
    return `<g stroke="#8A9870" stroke-linecap="round" fill="none">${stems}</g><g filter="url(#hr-soft)">${flowers}</g>`;
  }

  window.heroSVG = function () {
    const BLUE = ["#DAE9FA", "#A9C8EC", "#86A9D8"], PINK = ["#FACDD8", "#EEA0B6", "#D5809A"], YEL = ["#FDEDB4", "#F6D870", "#E2B64B"];
    return `<svg class="hero-svg" viewBox="0 0 972 560" role="img" aria-label="Um cartão com a mensagem Vamos celebrar, ao lado de um envelope, com balões e flores sobre um pódio" preserveAspectRatio="xMidYMid meet">
  <defs>
    <radialGradient id="hr-mint" cx="36%" cy="28%" r="85%"><stop offset="0" stop-color="#DFEFEA"/><stop offset="1" stop-color="#BCDCD1"/></radialGradient>
    <linearGradient id="hr-lav" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#E8DFF1"/><stop offset="1" stop-color="#CDBEE1"/></linearGradient>
    <linearGradient id="hr-lav2" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#F1EBF7" stop-opacity=".85"/><stop offset="1" stop-color="#E2D8EE" stop-opacity="0"/></linearGradient>
    <linearGradient id="hr-rose" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#F8E9E4"/><stop offset="1" stop-color="#EDD3CD"/></linearGradient>
    <linearGradient id="hr-arch" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#F9F3EA"/><stop offset="1" stop-color="#EFE5D7"/></linearGradient>
    <linearGradient id="hr-side" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#E8DECD"/><stop offset=".5" stop-color="#F2EADC"/><stop offset="1" stop-color="#E1D5C1"/></linearGradient>
    <linearGradient id="hr-top" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#FBF6EC"/><stop offset="1" stop-color="#EFE6D6"/></linearGradient>
    <linearGradient id="hr-env" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#FAF5EA"/><stop offset="1" stop-color="#ECE3D1"/></linearGradient>
    <linearGradient id="hr-flap" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#FDFAF2"/><stop offset="1" stop-color="#F1E9D9"/></linearGradient>
    <linearGradient id="hr-paper" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#F1ECF8"/><stop offset="1" stop-color="#E1D8EF"/></linearGradient>
    <linearGradient id="hr-gold" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#FBE38E"/><stop offset="1" stop-color="#EDB945"/></linearGradient>
    <linearGradient id="hr-fade" x1="0" y1="0" x2="0" y2="1"><stop offset=".8" stop-color="#fff"/><stop offset=".93" stop-color="#000"/></linearGradient>
    <mask id="hr-fade-m" maskUnits="userSpaceOnUse" x="0" y="0" width="972" height="560"><rect x="0" y="0" width="972" height="560" fill="url(#hr-fade)"/></mask>
    ${balloonGrad("blue", BLUE)}${balloonGrad("pink", PINK)}${balloonGrad("yel", YEL)}
    <filter id="hr-shadow" x="-25%" y="-20%" width="150%" height="150%"><feDropShadow dx="0" dy="14" stdDeviation="13" flood-color="#5A4764" flood-opacity=".22"/></filter>
    <filter id="hr-shadow-s" x="-20%" y="-20%" width="140%" height="150%"><feDropShadow dx="2" dy="6" stdDeviation="6" flood-color="#5A4764" flood-opacity=".18"/></filter>
    <filter id="hr-soft" x="-20%" y="-20%" width="140%" height="150%"><feDropShadow dx="0" dy="1" stdDeviation=".9" flood-color="#7A6A50" flood-opacity=".2"/></filter>
    <filter id="hr-blur"><feGaussianBlur stdDeviation="12"/></filter>
    <filter id="hr-floor" x="-10%" y="-80%" width="120%" height="260%"><feGaussianBlur stdDeviation="7"/></filter>
    <filter id="hr-grain" x="0" y="0" width="100%" height="100%"><feTurbulence type="fractalNoise" baseFrequency=".8" numOctaves="2" seed="7" result="n"/><feColorMatrix in="n" type="matrix" values="0 0 0 0 .4  0 0 0 0 .33  0 0 0 0 .46  0 0 0 .5 0"/></filter>
    <clipPath id="hr-card-clip"><path d="M325 160L597 128L642 470L355 488Z"/></clipPath>
    <g id="hr-fl"><g fill="#FFFDF8" stroke="#E2D6C0" stroke-width=".35"><ellipse cx="0" cy="-2.6" rx="1.7" ry="2.7"/><ellipse cx="0" cy="-2.6" rx="1.7" ry="2.7" transform="rotate(72)"/><ellipse cx="0" cy="-2.6" rx="1.7" ry="2.7" transform="rotate(144)"/><ellipse cx="0" cy="-2.6" rx="1.7" ry="2.7" transform="rotate(216)"/><ellipse cx="0" cy="-2.6" rx="1.7" ry="2.7" transform="rotate(288)"/></g><circle r="1" fill="#E6C063"/></g>
  </defs>

  <g data-depth="0.15"><circle cx="400" cy="272" r="250" fill="url(#hr-mint)"/></g>

  <g data-depth="0.3">
    <g mask="url(#hr-fade-m)">
      <path d="M636 252C690 236 744 232 796 248C862 268 920 302 972 322L972 520L636 520Z" fill="url(#hr-lav)"/>
      <path d="M690 262C740 250 790 262 850 292C896 314 940 326 972 330L972 520L690 520Z" fill="url(#hr-lav2)"/>
    </g>
    <path d="M972 316C928 372 872 424 800 466" fill="none" stroke="#B9A5C1" stroke-opacity=".7" stroke-width="1.3"/>
    <g mask="url(#hr-fade-m)"><path d="M12 458C50 392 118 338 206 322C250 315 286 316 318 322L338 470L12 470Z" fill="url(#hr-rose)"/></g>
    <path d="M186 470C190 392 236 322 308 296L340 300L346 470Z" fill="url(#hr-arch)" stroke="#E9DDCC" stroke-width="1.2"/>
    <ellipse cx="250" cy="476" rx="300" ry="24" fill="#FBF8F4" opacity=".95" filter="url(#hr-floor)"/>
  </g>

  <g data-depth="0.1">
    <ellipse cx="608" cy="520" rx="300" ry="28" fill="#5A4764" opacity=".2" filter="url(#hr-blur)"/>
    <path d="M326 490L326 534A282 38 0 0 0 890 534L890 490Z" fill="url(#hr-side)"/>
    <ellipse cx="608" cy="490" rx="282" ry="38" fill="url(#hr-top)"/>
  </g>

  <g data-depth="0.35"><g class="float" style="--dur:9s;--d:-2s">
    <path d="M377 78L612 132L642 246L690 452L292 452L296 296Z" fill="url(#hr-env)" filter="url(#hr-shadow-s)"/>
    <path d="M377 78L612 132L600 152L352 152Z" fill="url(#hr-flap)"/>
    <g filter="url(#hr-shadow)">
      <path d="M325 160L597 128L642 470L355 488Z" fill="url(#hr-paper)"/>
    </g>
    <g clip-path="url(#hr-card-clip)">
      <circle cx="600" cy="168" r="76" fill="#D9CDEA" fill-opacity=".85"/>
      <circle cx="336" cy="402" r="62" fill="#CDBFE2" fill-opacity=".7"/>
      <circle cx="446" cy="486" r="76" fill="#F3ECDD" fill-opacity=".92"/>
      <circle cx="648" cy="478" r="74" fill="#F2DDD6" fill-opacity=".85"/>
      <path d="M325 160L597 128L642 470L355 488Z" filter="url(#hr-grain)" opacity=".2"/>
    </g>
    <g transform="rotate(-6 408 272)" font-family="'Cormorant Garamond', Georgia, serif" font-size="52" font-weight="500" fill="#5E4E70" letter-spacing="-.4">
      <text x="404" y="272">Vamos</text><text x="404" y="328">celebrar</text>
    </g>
    ${star(508, 350, 11, "url(#hr-gold)", 0.6)}${star(541, 358, 7, "url(#hr-gold)", 1.4)}
    <path d="M452 378L520 372" stroke="#A596BF" stroke-width="1.5" stroke-linecap="round"/>
  </g></g>

  <g data-depth="0.9">
    ${balloon({ cx: 626, cy: 108, rx: 43, ry: 51, rot: -7, c: BLUE, id: "blue", dur: 7, delay: -1, end: [660, 290], sway: -14 })}
    ${balloon({ cx: 696, cy: 74, rx: 42, ry: 50, rot: 5, c: PINK, id: "pink", dur: 8, delay: -3, end: [668, 288], sway: 14 })}
    ${balloon({ cx: 733, cy: 148, rx: 45, ry: 53, rot: 9, c: YEL, id: "yel", dur: 6.5, delay: -5, end: [676, 292], sway: 12 })}
  </g>

  <g data-depth="0.35"><g class="float" style="--dur:9s;--d:-2s">
    <path d="M625 246L711 282L668 462L640 462Z" fill="url(#hr-flap)" stroke="#E6DBC6" stroke-width="1" filter="url(#hr-shadow-s)"/>
  </g></g>

  <g data-depth="0.6">
    ${sprig(150, 506, -42, 150, 5, 1)}
    ${sprig(154, 510, -9, 118, 17, 0.9)}
    ${sprig(668, 442, -26, 150, 31, 1)}
    ${sprig(672, 450, 4, 110, 41, 0.9)}
  </g>

  <g data-depth="1.2">
    ${star(238, 218, 19, "url(#hr-gold)", 0)}${star(203, 262, 12, "#B9A5C1", 1.1)}
    ${star(828, 217, 22, "url(#hr-gold)", 0.5)}${star(860, 258, 12, "#B9A5C1", 1.7)}
  </g>
</svg>`;
  };
})();
