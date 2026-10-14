/* Capas ilustradas provisórias (SVG gerado). Substituir pelas fotos reais dos kits.
   Linguagem do manual: arcos, curvas amplas, formas orgânicas, pontos e paleta reduzida. */
(function () {
  const INK = "#382F3E", WHITE = "#FFFFFF";
  const f = (c, o) => `fill="${c}"${o != null ? ` fill-opacity="${o}"` : ""}`;

  /* Cada motivo é desenhado em torno de (0,0), cabe em ~±80. a, b, c = paleta do kit. */
  const M = {
    bee: (a, b, c) => `<g transform="rotate(-8)">
      <ellipse cx="-14" cy="-34" rx="20" ry="30" transform="rotate(-24 -14 -34)" ${f(WHITE, .92)} stroke="${b}" stroke-width="3"/>
      <ellipse cx="22" cy="-34" rx="20" ry="30" transform="rotate(24 22 -34)" ${f(WHITE, .92)} stroke="${b}" stroke-width="3"/>
      <ellipse cx="0" cy="10" rx="52" ry="38" ${f(a)}/>
      <rect x="-26" y="-28" width="12" height="76" rx="6" ${f(INK, .85)} clip-path="inset(0 0 0 0)"/>
      <rect x="-2" y="-30" width="12" height="80" rx="6" ${f(INK, .85)}/>
      <rect x="22" y="-24" width="12" height="68" rx="6" ${f(INK, .85)}/>
      <circle cx="-56" cy="8" r="18" ${f(INK)}/><circle cx="-60" cy="4" r="3" ${f(WHITE)}/>
      <path d="M-62 -8 q-8 -18 -20 -20 M-52 -10 q2 -20 -6 -28" stroke="${INK}" stroke-width="3" fill="none" stroke-linecap="round"/></g>`,
    daisy: (a, b, c, mini) => {
      let p = ""; for (let i = 0; i < 12; i++) p += `<ellipse cx="0" cy="-44" rx="13" ry="30" transform="rotate(${i * 30})" ${f(WHITE)} stroke="${a}" stroke-width="2"/>`;
      return `${mini ? "" : `<path d="M0 40 q-6 50 6 90" stroke="${c}" stroke-width="5" fill="none" stroke-linecap="round" transform="translate(0,0)"/>`}${p}<circle r="22" ${f(b)}/><circle r="22" fill="none" stroke="${a}" stroke-width="2"/>`;
    },
    butterfly: (a, b, c) => `<g>
      <path d="M0 -6 C-30 -70 -92 -58 -78 -14 C-72 8 -30 10 0 4Z" ${f(a)}/>
      <path d="M0 6 C-26 8 -70 14 -58 52 C-48 82 -12 56 0 12Z" ${f(b)}/>
      <path d="M0 -6 C30 -70 92 -58 78 -14 C72 8 30 10 0 4Z" ${f(a)}/>
      <path d="M0 6 C26 8 70 14 58 52 C48 82 12 56 0 12Z" ${f(b)}/>
      <circle cx="-52" cy="-28" r="9" ${f(WHITE, .7)}/><circle cx="52" cy="-28" r="9" ${f(WHITE, .7)}/>
      <rect x="-5" y="-30" width="10" height="70" rx="5" ${f(c)}/>
      <path d="M-2 -28 q-10 -22 -22 -26 M2 -28 q10 -22 22 -26" stroke="${c}" stroke-width="3" fill="none" stroke-linecap="round"/></g>`,
    umbrella: (a, b, c) => `<g><path d="M-78 4 A78 78 0 0 1 78 4 q-26 -14 -52 0 q-26 -14 -52 0 q-26 -14 -52 0Z" ${f(a)}/>
      <path d="M-26 4 A26 70 0 0 1 0 -74 A26 70 0 0 1 26 4" fill="none" stroke="${WHITE}" stroke-opacity=".7" stroke-width="3"/>
      <path d="M0 4 V62 q0 18 -18 18" stroke="${c}" stroke-width="6" fill="none" stroke-linecap="round"/>
      <path d="M52 -74 q-14 -14 -24 0 q10 14 24 22 q14 -8 24 -22 q-10 -14 -24 0Z" transform="translate(26 -4) scale(.8)" ${f(b)}/></g>`,
    cherries: (a, b, c) => `<g><path d="M-30 52 Q-24 -10 18 -66 M34 40 Q30 -14 18 -66" stroke="${c}" stroke-width="5" fill="none" stroke-linecap="round"/>
      <path d="M18 -66 q34 -22 56 6 q-30 12 -56 -6Z" ${f(b)}/>
      <circle cx="-34" cy="56" r="34" ${f(a)}/><circle cx="36" cy="46" r="34" ${f(a)}/>
      <ellipse cx="-44" cy="46" rx="8" ry="12" ${f(WHITE, .5)} transform="rotate(20 -44 46)"/><ellipse cx="26" cy="36" rx="8" ry="12" ${f(WHITE, .5)} transform="rotate(20 26 36)"/></g>`,
    paw: (a, b, c) => `<g><ellipse cx="0" cy="34" rx="46" ry="38" ${f(a)}/>
      <ellipse cx="-52" cy="-14" rx="16" ry="22" transform="rotate(-24 -52 -14)" ${f(a)}/><ellipse cx="-18" cy="-44" rx="16" ry="23" transform="rotate(-8 -18 -44)" ${f(a)}/>
      <ellipse cx="18" cy="-44" rx="16" ry="23" transform="rotate(8 18 -44)" ${f(a)}/><ellipse cx="52" cy="-14" rx="16" ry="22" transform="rotate(24 52 -14)" ${f(a)}/>
      <ellipse cx="0" cy="36" rx="24" ry="18" ${f(WHITE, .45)}/></g>`,
    balloons: (a, b, c) => {
      const bl = (x, y, col, r) => `<g transform="translate(${x} ${y}) rotate(${r})"><ellipse rx="34" ry="42" ${f(col)}/><ellipse cx="-11" cy="-16" rx="7" ry="12" ${f(WHITE, .45)} transform="rotate(20 -11 -16)"/><path d="M-6 42 L6 42 L0 50Z" ${f(col)}/><path d="M0 50 q-10 24 4 46" stroke="${INK}" stroke-opacity=".5" stroke-width="2.5" fill="none"/></g>`;
      return bl(-38, -18, a, -8) + bl(40, -30, b, 10) + bl(4, 16, c === INK ? "#EDC9C1" : c, 0);
    },
    mushroom: (a, b, c) => `<g><path d="M-56 4 A56 56 0 0 1 56 4Z" ${f(a)}/><path d="M-24 4 V46 q0 14 24 14 q24 0 24 -14 V4Z" ${f(WHITE)} stroke="${b}" stroke-width="3"/>
      <circle cx="-26" cy="-22" r="9" ${f(WHITE, .9)}/><circle cx="10" cy="-34" r="11" ${f(WHITE, .9)}/><circle cx="34" cy="-8" r="7" ${f(WHITE, .9)}/>
      <path d="M62 -40 l4 10 10 4 -10 4 -4 10 -4 -10 -10 -4 10 -4Z" ${f(c)}/></g>`,
    crown: (a, b, c) => `<g><path d="M-62 36 L-72 -34 L-34 -2 L0 -50 L34 -2 L72 -34 L62 36Z" ${f(a)} stroke="${WHITE}" stroke-width="3" stroke-linejoin="round"/>
      <rect x="-62" y="36" width="124" height="18" rx="9" ${f(b)}/>
      <circle cx="-72" cy="-38" r="8" ${f(WHITE)}/><circle cx="0" cy="-54" r="9" ${f(WHITE)}/><circle cx="72" cy="-38" r="8" ${f(WHITE)}/>
      <circle cx="-30" cy="45" r="4" ${f(WHITE)}/><circle cx="0" cy="45" r="4" ${f(WHITE)}/><circle cx="30" cy="45" r="4" ${f(WHITE)}/></g>`,
    barn: (a, b, c) => `<g><path d="M-62 60 V-14 L0 -64 L62 -14 V60Z" ${f(a)}/><path d="M-72 -8 L0 -72 L72 -8" fill="none" stroke="${c}" stroke-width="7" stroke-linecap="round" stroke-linejoin="round"/>
      <rect x="-26" y="2" width="52" height="58" rx="3" ${f(WHITE)}/><path d="M-26 2 L26 60 M26 2 L-26 60" stroke="${a}" stroke-width="4"/><rect x="-26" y="2" width="52" height="58" rx="3" fill="none" stroke="${c}" stroke-width="4"/>
      <circle cx="0" cy="-26" r="9" ${f(WHITE)}/></g>`,
    moon: (a, b, c) => `<g><path d="M26 -70 A72 72 0 1 0 60 36 A58 58 0 0 1 26 -70Z" ${f(a)}/>
      <path d="M52 -42 l5 13 13 5 -13 5 -5 13 -5 -13 -13 -5 13 -5Z" ${f(b)}/><path d="M-4 -8 l3 8 8 3 -8 3 -3 8 -3 -8 -8 -3 8 -3Z" ${f(WHITE)}/><circle cx="70" cy="22" r="5" ${f(WHITE)}/></g>`,
    cat: (a, b, c) => `<g><path d="M-62 -6 L-56 -64 L-18 -34Z" ${f(a)}/><path d="M62 -6 L56 -64 L18 -34Z" ${f(a)}/>
      <path d="M-50 -14 L-48 -46 L-28 -30Z" ${f(b, .8)}/><path d="M50 -14 L48 -46 L28 -30Z" ${f(b, .8)}/>
      <ellipse cx="0" cy="12" rx="66" ry="56" ${f(a)}/><circle cx="-24" cy="2" r="7" ${f(INK)}/><circle cx="24" cy="2" r="7" ${f(INK)}/>
      <path d="M-7 20 h14 l-7 9Z" ${f(b)}/><path d="M0 29 q-8 10 -16 6 M0 29 q8 10 16 6" stroke="${INK}" stroke-width="3" fill="none" stroke-linecap="round"/>
      <path d="M-40 22 h-38 M-40 32 l-34 8 M40 22 h38 M40 32 l34 8" stroke="${INK}" stroke-opacity=".6" stroke-width="2.5" stroke-linecap="round"/></g>`,
    bunny: (a, b, c) => `<g><ellipse cx="-24" cy="-52" rx="15" ry="38" transform="rotate(-10 -24 -52)" ${f(a)}/><ellipse cx="24" cy="-52" rx="15" ry="38" transform="rotate(10 24 -52)" ${f(a)}/>
      <ellipse cx="-24" cy="-52" rx="7" ry="26" transform="rotate(-10 -24 -52)" ${f(b, .55)}/><ellipse cx="24" cy="-52" rx="7" ry="26" transform="rotate(10 24 -52)" ${f(b, .55)}/>
      <circle cx="0" cy="22" r="52" ${f(a)}/><circle cx="-18" cy="14" r="5.5" ${f(INK)}/><circle cx="18" cy="14" r="5.5" ${f(INK)}/>
      <ellipse cx="0" cy="30" rx="8" ry="6" ${f("#E5707E")}/><path d="M0 36 v8 M0 44 q-8 8 -14 2 M0 44 q8 8 14 2" stroke="${INK}" stroke-width="2.5" fill="none" stroke-linecap="round"/></g>`,
    dog: (a, b, c) => `<g><ellipse cx="-58" cy="0" rx="22" ry="44" transform="rotate(14 -58 0)" ${f(b)}/><ellipse cx="58" cy="0" rx="22" ry="44" transform="rotate(-14 58 0)" ${f(b)}/>
      <ellipse cx="0" cy="0" rx="52" ry="58" ${f(a)}/><ellipse cx="0" cy="22" rx="28" ry="22" ${f(WHITE, .65)}/>
      <circle cx="-20" cy="-14" r="6" ${f(INK)}/><circle cx="20" cy="-14" r="6" ${f(INK)}/><ellipse cx="0" cy="14" rx="10" ry="7" ${f(INK)}/>
      <path d="M0 21 v10 M0 31 q-9 9 -16 2 M0 31 q9 9 16 2" stroke="${INK}" stroke-width="2.5" fill="none" stroke-linecap="round"/></g>`,
    heartballoon: (a, b, c) => {
      const h = (x, y, col, s, r) => `<g transform="translate(${x} ${y}) rotate(${r}) scale(${s})"><path d="M0 44 C-70 -2 -44 -62 0 -26 C44 -62 70 -2 0 44Z" ${f(col)}/><path d="M-26 -22 q-12 8 -10 22" stroke="${WHITE}" stroke-opacity=".6" stroke-width="5" fill="none" stroke-linecap="round"/><path d="M0 44 l-6 8 h12Z" ${f(col)}/><path d="M0 52 q-10 22 6 44" stroke="${INK}" stroke-opacity=".5" stroke-width="2.2" fill="none"/></g>`;
      return h(-30, -10, a, 1.05, -8) + h(38, 4, b, .8, 12);
    },
    kite: (a, b, c) => `<g transform="rotate(14)"><path d="M0 -80 L50 -10 L0 56 L-50 -10Z" ${f(a)}/><path d="M0 -80 L0 56 M-50 -10 H50" stroke="${WHITE}" stroke-opacity=".7" stroke-width="3"/>
      <path d="M0 56 q-22 24 0 44 q22 20 0 40" stroke="${INK}" stroke-opacity=".5" stroke-width="2.5" fill="none"/>
      <path d="M-4 76 l-16 -8 v16Z M4 76 l16 -8 v16Z" ${f(b)} transform="translate(0 6)"/><path d="M-4 104 l-16 -8 v16Z M4 104 l16 -8 v16Z" ${f(c === INK ? b : c)} transform="translate(0 4)"/></g>`,
    sun: (a, b, c) => {
      let r = ""; for (let i = 0; i < 14; i++) r += `<rect x="-5" y="-84" width="10" height="26" rx="5" transform="rotate(${i * (360 / 14)})" ${f(a)}/>`;
      return `${r}<circle r="46" ${f(a)}/><circle cx="-16" cy="-10" r="5" ${f(INK)}/><circle cx="16" cy="-10" r="5" ${f(INK)}/><path d="M-20 10 q20 22 40 0" stroke="${INK}" stroke-width="4" fill="none" stroke-linecap="round"/><circle cx="-28" cy="8" r="7" ${f("#F08F7C", .5)}/><circle cx="28" cy="8" r="7" ${f("#F08F7C", .5)}/>`;
    },
    bird: (a, b, c) => `<g><path d="M-70 44 C-70 -2 -22 4 -8 -18 C-4 -50 -2 -64 20 -66 C44 -66 44 -34 26 -22 C20 -4 34 -2 62 8 C74 36 40 60 -8 60 C-40 60 -62 56 -70 44Z" ${f(a)}/>
      <path d="M-40 28 C-26 6 8 12 22 34 C-2 50 -30 48 -40 28Z" ${f(WHITE, .55)}/><path d="M40 -52 l32 8 -30 14Z" ${f("#F2A65A")}/><circle cx="28" cy="-52" r="4.5" ${f(INK)}/>
      <path d="M-14 62 v18 M14 62 v18" stroke="#F2A65A" stroke-width="5" stroke-linecap="round"/></g>`,
    sparkle: (a, b, c) => {
      const s = (x, y, k, col) => `<path transform="translate(${x} ${y}) scale(${k})" d="M0 -40 C4 -14 14 -4 40 0 C14 4 4 14 0 40 C-4 14 -14 4 -40 0 C-14 -4 -4 -14 0 -40Z" ${f(col)}/>`;
      return s(-6, 4, 1.45, a) + s(58, -50, .62, b) + s(-56, -54, .5, c === INK ? b : c) + s(52, 52, .42, WHITE) + `<circle cx="-62" cy="46" r="5" ${f(b)}/>`;
    },
    strawberry: (a, b, c) => { let s = ""; [[-26, -8], [4, -18], [30, -4], [-12, 18], [18, 22], [0, 46], [-34, 30], [36, 34]].forEach(([x, y]) => s += `<ellipse cx="${x}" cy="${y}" rx="3.4" ry="5.4" ${f("#FFF3C4")}/>`);
      return `<g><path d="M-62 -22 C-62 -44 62 -44 62 -22 C62 26 20 74 0 74 C-20 74 -62 26 -62 -22Z" ${f(a)}/>${s}
      <path d="M0 -36 l-34 -14 20 -6 14 -18 14 18 20 6Z" ${f(c)}/><path d="M0 -62 v-18" stroke="${c}" stroke-width="5" stroke-linecap="round"/></g>`; },
    tent: (a, b, c) => `<g><path d="M-74 66 V-4 L0 -66 L74 -4 V66Z" ${f(WHITE)}/>
      <path d="M0 -66 L-74 -4 H74Z" ${f(a)}/><path d="M-50 -4 L0 -66 L-26 -4Z M26 -4 L0 -66 L50 -4Z" ${f(b)}/>
      <path d="M-74 -4 q12 14 24 0 q12 14 24 0 q12 14 24 0 q12 14 24 0 q12 14 24 0 q12 14 24 0" ${f(a)}/>
      <path d="M-74 -4 v70 M74 -4 v70" stroke="${a}" stroke-width="3"/><path d="M-18 66 V24 q18 -26 36 0 V66Z" ${f(c)}/>
      <path d="M0 -66 V-86 l22 7 -22 7" ${f(b)} stroke="${c}" stroke-width="3" stroke-linejoin="round"/></g>`,
    rainbow: (a, b, c) => `<g fill="none" stroke-linecap="round" stroke-width="15"><path d="M-72 56 A72 72 0 0 1 72 56" stroke="${a}"/><path d="M-52 56 A52 52 0 0 1 52 56" stroke="#F2DFB4"/><path d="M-32 56 A32 32 0 0 1 32 56" stroke="${b}"/></g>
      <g ${f(WHITE)}><circle cx="-80" cy="58" r="17"/><circle cx="-64" cy="64" r="15"/><circle cx="-92" cy="66" r="12"/><circle cx="80" cy="58" r="17"/><circle cx="64" cy="64" r="15"/><circle cx="92" cy="66" r="12"/></g>`,
    seasons: (a, b, c) => `<g><path d="M0 0 L0 -74 A74 74 0 0 1 74 0Z" ${f("#9DD2C8")}/><path d="M0 0 L74 0 A74 74 0 0 1 0 74Z" ${f("#F2C94C")}/>
      <path d="M0 0 L0 74 A74 74 0 0 1 -74 0Z" ${f("#E58C8A")}/><path d="M0 0 L-74 0 A74 74 0 0 1 0 -74Z" ${f("#B9A5C1")}/>
      <circle r="74" fill="none" stroke="${WHITE}" stroke-width="5"/><circle r="14" ${f(WHITE)}/></g>`,
    scales: (a, b, c) => { let s = ""; for (let y = 0; y < 5; y++) for (let x = 0; x < 5; x++) { const cx = -64 + x * 32 + (y % 2 ? 16 : 0), cy = -52 + y * 24; s += `<path d="M${cx - 16} ${cy} A16 16 0 0 0 ${cx + 16} ${cy}" fill="none" stroke="${(x + y) % 2 ? a : b}" stroke-width="5" stroke-linecap="round"/>`; }
      return `<g><path d="M0 -76 C46 -64 76 -24 62 24 C52 58 12 76 0 76 C-12 76 -52 58 -62 24 C-76 -24 -46 -64 0 -76Z" ${f(WHITE, .85)} stroke="${a}" stroke-width="3"/>${s}</g>`; },
    tie: (a, b, c) => `<g><path d="M-24 -62 H24 L16 -34 H-16Z" ${f(a)} stroke="${WHITE}" stroke-width="3" stroke-linejoin="round"/>
      <path d="M-16 -34 H16 L40 56 L0 78 L-40 56Z" ${f(a)} stroke="${WHITE}" stroke-width="3" stroke-linejoin="round"/>
      <path d="M-24 6 L24 -10 M-30 30 L30 14" stroke="${b}" stroke-width="8" stroke-linecap="round"/></g>`,
    car: (a, b, c) => `<g><path d="M-80 28 Q-80 6 -58 4 L-40 -30 Q-34 -42 -20 -42 H26 Q38 -42 46 -30 L60 4 Q80 8 80 28 V40 H-80Z" ${f(a)}/>
      <path d="M-30 -32 H22 Q30 -32 34 -24 L44 2 H-48Z" ${f(WHITE, .85)}/><path d="M-6 -34 V2" stroke="${a}" stroke-width="4"/>
      <circle cx="-44" cy="42" r="19" ${f(INK)}/><circle cx="44" cy="42" r="19" ${f(INK)}/><circle cx="-44" cy="42" r="8" ${f(b)}/><circle cx="44" cy="42" r="8" ${f(b)}/>
      <rect x="62" y="12" width="14" height="9" rx="4" ${f("#F2C94C")}/></g>`,
    seven: (a, b, c) => `<g><circle r="76" ${f(WHITE, .8)} stroke="${a}" stroke-width="4"/><circle r="64" fill="none" stroke="${b}" stroke-width="3" stroke-dasharray="2 9" stroke-linecap="round"/>
      <text x="0" y="40" text-anchor="middle" font-family="Cormorant Garamond, Georgia, serif" font-weight="600" font-size="118" ${f(c === INK ? "#65516F" : c)}>7</text></g>`,
    hood: (a, b, c) => `<g><path d="M0 -76 C-44 -70 -66 -28 -62 20 C-60 48 -72 64 -80 70 C-40 62 40 62 80 70 C72 64 60 48 62 20 C66 -28 44 -70 0 -76Z" ${f(a)}/>
      <path d="M0 -76 C-22 -52 -22 -4 0 18 C22 -4 22 -52 0 -76Z" ${f("#FFF3E6")}/><path d="M0 -76 C-22 -52 -22 -4 0 18" stroke="${INK}" stroke-opacity=".25" stroke-width="2" fill="none"/>
      <circle cx="0" cy="-8" r="8" ${f(INK)} fill-opacity="0"/><path d="M-62 20 q62 26 124 0" stroke="${b}" stroke-width="5" fill="none" stroke-linecap="round"/></g>`,
    dots: (a, b, c) => { let s = ""; for (let y = 0; y < 5; y++) for (let x = 0; x < 5; x++) s += `<circle cx="${-64 + x * 32}" cy="${-64 + y * 32}" r="${(x + y) % 2 ? 9 : 13}" ${f((x * y) % 3 ? a : b)}/>`; return s; },
    tree: (a, b, c) => `<g><path d="M0 -80 L-44 -22 H-22 L-58 24 H-28 L-68 66 H68 L28 24 H58 L22 -22 H44Z" ${f(a)}/><rect x="-10" y="66" width="20" height="18" rx="3" ${f("#A67C5B")}/>
      <circle cx="-14" cy="-10" r="6" ${f(b)}/><circle cx="18" cy="14" r="6" ${f("#F2C94C")}/><circle cx="-20" cy="40" r="6" ${f("#F2C94C")}/><circle cx="26" cy="48" r="6" ${f(b)}/>
      <path d="M0 -102 l5 12 12 5 -12 5 -5 12 -5 -12 -12 -5 12 -5Z" ${f("#F2C94C")}/></g>`,
    cup: (a, b, c) => `<g><path d="M-58 -14 H46 V28 A52 44 0 0 1 -58 28Z" ${f(WHITE)} stroke="${a}" stroke-width="5"/><path d="M46 0 h14 a20 20 0 0 1 0 40 h-18" fill="none" stroke="${a}" stroke-width="7" stroke-linecap="round"/>
      <path d="M-58 -2 H46" stroke="${b}" stroke-width="8"/><ellipse cx="0" cy="84" rx="64" ry="9" ${f(a, .55)}/>
      <path d="M-26 -30 q-12 -14 0 -26 q12 -14 0 -28 M10 -30 q-12 -14 0 -26 q12 -14 0 -28" stroke="${b}" stroke-width="5" fill="none" stroke-linecap="round"/></g>`
  };

  /* ---------- Capa do kit: cartão de papel com varal, flores, envelope e etiqueta (como a foto de referência) ---------- */
  const rng = (seed) => { let s = seed >>> 0; return () => { s = (s * 1664525 + 1013904223) >>> 0; return s / 4294967296; }; };
  const SAGE = "#A9C2B3", STEM = "#8FB09F";
  const n1 = (v) => v.toFixed(1);

  /* ramo de flor-do-campo: haste curva, galhos finos e florezinhas brancas */
  function sprig(x0, y0, ang, len, seed) {
    const r = rng(seed), rad = ang * Math.PI / 180;
    const x1 = x0 + Math.cos(rad) * len, y1 = y0 + Math.sin(rad) * len;
    const qx = x0 + Math.cos(rad - .42) * len * .55, qy = y0 + Math.sin(rad - .42) * len * .55;
    const at = (t) => { const u = 1 - t; return [u * u * x0 + 2 * u * t * qx + t * t * x1, u * u * y0 + 2 * u * t * qy + t * t * y1]; };
    let s = `<path d="M${n1(x0)} ${n1(y0)}Q${n1(qx)} ${n1(qy)} ${n1(x1)} ${n1(y1)}" fill="none" stroke="${STEM}" stroke-width="1.8" stroke-linecap="round"/>`, fl = "";
    const bloom = (x, y, k) => { fl += `<circle cx="${n1(x)}" cy="${n1(y)}" r="${n1(4.3 * k)}" fill="#fff" stroke="#E9E4EC" stroke-width=".5"/><circle cx="${n1(x)}" cy="${n1(y)}" r="${n1(1.2 * k)}" fill="#F2DFB4"/>`; };
    for (let i = 0; i < 12; i++) {
      const t = .14 + .86 * (i / 11), [x, y] = at(t), side = i % 2 ? 1 : -1, a = rad + side * (.55 + r() * .6), l = 14 + r() * 20;
      const bx = x + Math.cos(a) * l, by = y + Math.sin(a) * l;
      s += `<path d="M${n1(x)} ${n1(y)}L${n1(bx)} ${n1(by)}" stroke="${STEM}" stroke-width="1.2" stroke-linecap="round"/>`;
      bloom(bx, by, 1 + r() * .35); bloom((x + bx) / 2 + r() * 4 - 2, (y + by) / 2 + r() * 4 - 2, .85);
      if (i % 3 === 0) { const a2 = a + side * .9, l2 = l * .7; bloom(x + Math.cos(a2) * l2, y + Math.sin(a2) * l2, .9); }
    }
    bloom(x1, y1, 1.1);
    return s + fl;
  }
  /* ramo de eucalipto: folhas redondas e acinzentadas */
  function eucalyptus(x0, y0, ang, len, seed) {
    const r = rng(seed), rad = ang * Math.PI / 180, x1 = x0 + Math.cos(rad) * len, y1 = y0 + Math.sin(rad) * len;
    const qx = x0 + Math.cos(rad + .35) * len * .5, qy = y0 + Math.sin(rad + .35) * len * .5;
    let s = `<path d="M${n1(x0)} ${n1(y0)}Q${n1(qx)} ${n1(qy)} ${n1(x1)} ${n1(y1)}" fill="none" stroke="#7E9C8B" stroke-width="2" stroke-linecap="round"/>`;
    for (let i = 0; i < 8; i++) {
      const t = .12 + .88 * (i / 7), u = 1 - t, x = u * u * x0 + 2 * u * t * qx + t * t * x1, y = u * u * y0 + 2 * u * t * qy + t * t * y1;
      const side = i % 2 ? 1 : -1, a = (rad + side * (1.05 + r() * .3)) * 180 / Math.PI, k = 1 - t * .35;
      s += `<ellipse cx="${n1(x)}" cy="${n1(y)}" rx="${n1(8.5 * k)}" ry="${n1(11 * k)}" transform="rotate(${n1(a + 90)} ${n1(x)} ${n1(y)}) translate(0 ${n1(-9 * k)})" fill="${i % 3 ? SAGE : "#B9CFC1"}"/>`;
    }
    return s;
  }
  /* varal de bandeirinhas ao longo de uma curva quadrática P0(52,24) C(196,58) P1(340,24) */
  function bunting(a, b, c) {
    const cols = [a, "#F7EFE6", b, "#F2DFB4", c === INK ? SAGE : c], N = 9;
    let flags = "";
    for (let i = 0; i < N; i++) {
      const t = (i + .5) / N, u = 1 - t, x = u * u * 52 + 2 * u * t * 196 + t * t * 340, y = u * u * 24 + 2 * u * t * 58 + t * t * 24;
      const ang = Math.atan2(2 * u * 34 + 2 * t * -34, 288) * 180 / Math.PI;
      flags += `<path transform="rotate(${n1(ang)} ${n1(x)} ${n1(y)})" d="M${n1(x - 13)} ${n1(y)}h26l-13 27Z" fill="${cols[i % cols.length]}" stroke="#382F3E" stroke-opacity=".12" stroke-width=".8"/>`;
    }
    return `<path d="M52 24Q196 58 340 24" fill="none" stroke="#382F3E" stroke-opacity=".3" stroke-width="1.6" stroke-linecap="round"/>${flags}`;
  }

  window.coverSVG = function (p, uid, mode) { /* mode: "wide" = miniatura retangular (corta o rodapé da arte) · "grande" = papel na cor do kit, para o cartão grande */
    const wide = mode === "wide", grande = mode === "grande";
    const [a, b, c, bg] = p.p, g = `g${uid}`, tilt = p.id % 2 ? 3.2 : -2.4, S = p.id * 11;
    const big = (M[p.m] || M.sparkle)(a, b, c), mini = (M[p.m] || M.sparkle)(a, b, c, true);
    const dy = p.m === "daisy" ? 186 : 204;
    const leaf = p.id % 3 === 0;
    return `<svg class="cover-svg" viewBox="${wide ? "0 20 400 326" : "0 0 400 392"}" role="img" aria-label="Capa ilustrativa do kit ${p.nome}" xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="xMidYMid slice">
      <defs><linearGradient id="${g}" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="${a}" stop-opacity=".16"/><stop offset="1" stop-color="${a}" stop-opacity=".66"/></linearGradient>
      <radialGradient id="${g}r"><stop offset="0" stop-color="#fff" stop-opacity=".7"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></radialGradient>
      <filter id="${g}s" x="-30%" y="-30%" width="160%" height="170%"><feDropShadow dx="0" dy="8" stdDeviation="7" flood-color="#382F3E" flood-opacity=".22"/></filter>
      <filter id="${g}k" x="-20%" y="-10%" width="140%" height="130%"><feDropShadow dx="0" dy="6" stdDeviation="9" flood-color="#382F3E" flood-opacity=".17"/></filter>
      <clipPath id="${g}t"><circle r="47"/></clipPath></defs>
      <rect width="400" height="392" fill="${bg}"/><rect width="400" height="392" fill="url(#${g})"/>
      <circle cx="60" cy="330" r="96" fill="url(#${g}r)"/><circle cx="352" cy="36" r="74" fill="url(#${g}r)"/><circle cx="230" cy="372" r="60" fill="url(#${g}r)" opacity=".7"/>
      <g transform="rotate(-9 300 250)"><rect x="176" y="104" width="270" height="262" rx="10" fill="${a}" fill-opacity="${grande ? .46 : .34}"/>
        <path d="M176 106L311 226L446 106" fill="none" stroke="#fff" stroke-opacity=".55" stroke-width="2"/><path d="M176 366L292 244M446 366L330 244" fill="none" stroke="#fff" stroke-opacity=".3" stroke-width="1.6"/></g>
      <g transform="rotate(${tilt} 196 196)">
        <rect x="44" y="-18" width="304" height="432" rx="10" fill="${grande ? bg : "#fff"}" filter="url(#${g}k)"/>
        <rect x="62" y="62" width="268" height="318" rx="26" fill="none" stroke="${a}" stroke-opacity=".7" stroke-width="1.6" stroke-dasharray="2.5 5.5" stroke-linecap="round"/>
        <circle cx="196" cy="${dy}" r="110" fill="${a}" fill-opacity=".2"/><circle cx="196" cy="${dy}" r="88" fill="${b}" fill-opacity=".24"/>
        <g fill="${a}" fill-opacity=".5">${[0, 1, 2, 3, 4, 5, 6].map((i) => `<circle cx="${100 + i * 32}" cy="${362 + (i % 2) * 5}" r="2.6"/>`).join("")}</g>
        ${bunting(a, b, c)}
        <g transform="translate(196 ${dy}) scale(1.3)" filter="url(#${g}s)">${big}</g>
      </g>
      <g>${leaf ? eucalyptus(-8, 70, 52, 120, S + 5) + eucalyptus(-6, 250, -50, 150, S + 9) : ""}${sprig(-6, 392, -66, 210, S + 1)}${sprig(-4, 330, -38, 130, S + 3)}${sprig(-8, 40, 38, 100, S + 7)}</g>
      <g transform="translate(326 288) rotate(-8)"><path d="M0 -50C4 -88 44 -112 82 -120" fill="none" stroke="#382F3E" stroke-opacity=".34" stroke-width="1.4"/>
        <circle r="58" fill="#fff" filter="url(#${g}s)"/><circle r="51" fill="${a}" fill-opacity=".26"/><circle cx="0" cy="-45" r="4.6" fill="${bg}" stroke="${a}" stroke-opacity=".8" stroke-width="1.4"/>
        <g clip-path="url(#${g}t)"><g transform="translate(0 5) scale(.58)">${mini}</g></g></g>
    </svg>`;
  };

  /* Desenho avulso (sem moldura) para os cartões de ocasião. pal = [principal, secundária, acento]. */
  window.motifSVG = function (name, pal) {
    const [a, b, c] = pal;
    return `<svg viewBox="-120 -110 240 240" overflow="visible" aria-hidden="true" xmlns="http://www.w3.org/2000/svg">${(M[name] || M.sparkle)(a, b, c)}</svg>`;
  };
})();
