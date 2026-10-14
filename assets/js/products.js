/* CATÁLOGO PROVISÓRIO.
   Nomes e preços vieram da página Festa Digital da Joy in the Box (consulta em 13/10/2026),
   por pedido do projeto, só para montar o layout. NÃO são os produtos da Criando Memórias.
   Antes de publicar: trocar por produtos, preços e fotos reais e conferir tema, ocasião e tipo.
   Ficaram de fora temas de personagens licenciados (Hot Wheels, Harry Potter, Mickey e Minnie).
   Parcelamento da referência também não foi copiado: condições de pagamento são da loja.

   Campos: m = motivo da capa ilustrada · p = paleta [principal, secundária, acento, fundo suave]
           d = destaque na página inicial */
window.TIPOS = {
  kit:        { rotulo: "Kit digital",                    grupo: "Kits digitais" },
  mesa:       { rotulo: "Kit para mesa posta",            grupo: "Mesa posta e cestas" },
  cesta:      { rotulo: "Kit para cesta",                 grupo: "Mesa posta e cestas" },
  mesacesta:  { rotulo: "Kit para cesta ou mesa posta",   grupo: "Mesa posta e cestas" },
  molde:      { rotulo: "Arquivo digital de molde",       grupo: "Moldes e arquivos" },
  arquivo:    { rotulo: "Arquivo digital",                grupo: "Moldes e arquivos" }
};

(function () {
  const INF = "Festa infantil", BEB = "Chá de bebê", ADU = "Festa adulto", DAT = "Datas comemorativas";
  const JAR = "Jardim e natureza", BIC = "Bichinhos", FAN = "Fantasia e princesas", BAL = "Balões e cores", DIV = "Outros temas";
  /* [nome, tipo, ocasião, tema, preço, motivo, paleta, destaque] */
  const L = [
    ["Festa Abelhinha",               "kit",       INF, JAR, 74.90, "bee",        ["#F2C94C","#F2DFB4","#65516F","#FFF7DC"], 1],
    ["Festa Margarida",               "kit",       INF, JAR, 74.90, "daisy",      ["#F4B6A6","#F2DFB4","#28594F","#FFF1EC"], 1],
    ["Festa Jardim de Borboletas",    "kit",       INF, JAR, 74.90, "butterfly",  ["#B9A5C1","#9DD2C8","#65516F","#F3EEF7"], 1],
    ["Guarda-chuva de Amor",          "molde",     DAT, DIV, 29.90, "umbrella",   ["#EDC9C1","#B9A5C1","#65516F","#FDF0EC"], 0],
    ["Festa Cerejinha",               "kit",       INF, JAR, 74.90, "cherries",   ["#E58C8A","#9DD2C8","#28594F","#FFF0EE"], 0],
    ["Festa Capivara",                "kit",       INF, BIC, 74.90, "paw",        ["#C9A27A","#9DD2C8","#382F3E","#FBF1E7"], 0],
    ["Festa Balão Menino",            "kit",       INF, BAL, 74.90, "balloons",   ["#8CB8D9","#9DD2C8","#382F3E","#EAF4FA"], 0],
    ["Festa Jardim de Fadas",         "kit",       INF, FAN, 74.90, "mushroom",   ["#E58C8A","#B9A5C1","#28594F","#FDF0F3"], 0],
    ["Mesa posta Princesa",           "mesa",      INF, FAN, 39.90, "crown",      ["#E6BE5A","#EDC9C1","#65516F","#FFF6E0"], 0],
    ["Festa Fazendinha (mini table)", "kit",       INF, BIC, 74.90, "barn",       ["#D9826B","#F2DFB4","#28594F","#FFF3E8"], 0],
    ["Chá de Bebê Anunciação",        "kit",       BEB, DIV, 74.90, "moon",       ["#B9C8E6","#F2DFB4","#65516F","#F1F4FB"], 0],
    ["Festa Gatinhos",                "kit",       INF, BIC, 74.90, "cat",        ["#E7B79B","#B9A5C1","#382F3E","#FDF2EA"], 0],
    ["Festa Princesas",               "kit",       INF, FAN, 63.90, "crown",      ["#E49BB6","#F2DFB4","#65516F","#FEEFF5"], 0],
    ["Páscoa (Coelhinho)",            "cesta",     DAT, DIV, 29.90, "bunny",      ["#F2C9CE","#9DD2C8","#65516F","#FFF1F2"], 0],
    ["Festa Cachorrinho Menina",      "kit",       INF, BIC, 74.90, "dog",        ["#D9A87C","#EDC9C1","#382F3E","#FBF0E6"], 0],
    ["Festa Balão Coração",           "kit",       INF, BAL, 74.90, "heartballoon",["#E58C9A","#B9A5C1","#65516F","#FEEFF2"], 0],
    ["Mesa posta Dia das Crianças",   "mesa",      DAT, BAL, 29.90, "kite",       ["#7FC4B8","#F2C94C","#382F3E","#EAF7F4"], 0],
    ["Festa You Are My Sunshine",     "kit",       INF, BAL, 74.90, "sun",        ["#F2C94C","#9DD2C8","#65516F","#FFF8DD"], 0],
    ["Festa Ganso",                   "kit",       INF, BIC, 74.90, "bird",       ["#9DD2C8","#F2DFB4","#382F3E","#EDF8F5"], 0],
    ["Festa Fada",                    "kit",       INF, FAN, 74.90, "sparkle",    ["#B9A5C1","#EDC9C1","#28594F","#F5F0F8"], 0],
    ["Festa Moranguinho",             "kit",       INF, JAR, 74.90, "strawberry", ["#E5707E","#9DD2C8","#28594F","#FFEFF1"], 0],
    ["Festa Circo Coral",             "kit",       INF, DIV, 74.90, "tent",       ["#F08F7C","#F2DFB4","#65516F","#FFF1EC"], 0],
    ["Festa Princesa",                "kit",       INF, FAN, 74.90, "crown",      ["#B9A5C1","#F2C94C","#65516F","#F5F0F8"], 0],
    ["Festa Arco-íris Boho",          "kit",       INF, BAL, 74.90, "rainbow",    ["#EDC9C1","#9DD2C8","#65516F","#FDF3EE"], 1],
    ["Capivara Menina (cesta ou mesa posta)","mesacesta",INF,BIC,29.90,"paw",     ["#EDC9C1","#C9A27A","#382F3E","#FDF1EC"], 0],
    ["Festa 4 Estações",              "kit",       INF, JAR, 74.90, "seasons",    ["#9DD2C8","#F2DFB4","#65516F","#EEF8F5"], 0],
    ["Festa Sereia",                  "kit",       INF, FAN, 74.90, "scales",     ["#7FC4B8","#B9A5C1","#28594F","#E9F7F4"], 1],
    ["Dia dos Pais (cesta)",          "cesta",     DAT, DIV, 29.90, "tie",        ["#8CA6C9","#F2DFB4","#382F3E","#EDF2FA"], 0],
    ["Festa Capivara Menina",         "kit",       INF, BIC, 74.90, "paw",        ["#EDC9C1","#9DD2C8","#65516F","#FDF1EC"], 0],
    ["Festa Carrinhos Cidade",        "kit",       INF, DIV, 74.90, "car",        ["#E8806B","#9DD2C8","#382F3E","#FFF0EC"], 0],
    ["Festa Bailarina",               "kit",       INF, FAN, 74.90, "sparkle",    ["#EDB5C6","#F2DFB4","#65516F","#FEF0F5"], 0],
    ["Festa Pintando o 7",            "kit",       INF, BAL, 74.90, "seven",      ["#9DD2C8","#F2C94C","#65516F","#EEF8F5"], 0],
    ["Dia dos Pais (cesta ou mesa posta)","mesacesta",DAT,DIV,29.90,"tie",        ["#B9A5C1","#9DD2C8","#382F3E","#F5F0F8"], 0],
    ["Festa Chapeuzinho Vermelho (painel grande)","kit",INF,FAN,63.90,"hood",     ["#D9604F","#F2DFB4","#382F3E","#FFF0EC"], 0],
    ["Estampas Balão Menino",         "arquivo",   INF, BAL, 29.90, "dots",       ["#8CB8D9","#9DD2C8","#382F3E","#EAF4FA"], 0],
    ["Festa Natal",                   "kit",       DAT, DIV, 74.90, "tree",       ["#4F9A83","#E5707E","#382F3E","#EAF6F1"], 0],
    ["Chá de Cozinha",                "kit",       ADU, DIV, 63.90, "cup",        ["#EDC9C1","#9DD2C8","#65516F","#FDF2EE"], 0]
  ];
  const slug = (s) => s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "");
  window.PRODUTOS = L.map((r, i) => ({
    id: i + 1, slug: slug(r[0]), nome: r[0], tipo: r[1], ocasiao: r[2], tema: r[3],
    preco: r[4], m: r[5], p: r[6], d: !!r[7]
  }));
  /* texto de apresentação (seção "Em destaque"): [chamada, descrição]; sem isso, a seção usa a ocasião e um texto genérico */
  const COPY = { "festa-abelhinha": ["Para celebrar com doçura", "Um tema delicado para transformar a sua festa."] };
  window.PRODUTOS.forEach((p) => { const c = COPY[p.slug]; if (c) { p.chamada = c[0]; p.texto = c[1]; } });
})();
