/* Criando Memórias — configuração editável do site.
   Tudo que o cliente pode querer trocar sem mexer no layout fica aqui. */
window.SITE = {
  nome: "Criando Memórias",

  /* WhatsApp de atendimento, com DDI e DDD, só números. Ex.: "5511999999999".
     Enquanto estiver vazio, o botão "Consultar este kit" copia a mensagem e avisa que o canal está em configuração. */
  whatsapp: "",

  /* Barra promocional no topo. Troque os textos quando a promoção real estiver definida.
     Coloque ativa: false para esconder a barra. */
  promo: {
    ativa: true,
    mensagens: [
      "Promoção de lançamento",
      "Kits digitais para a sua celebração",
      "Consulte as condições"
    ],
    link: { texto: "Ver os kits", href: "#catalogo" }
  },

  /* Loja: carrinho, login e pagamento (a API está em backend/, veja backend/README.md).
     api = endereço da API. Aberto por arquivo (file://) ou em localhost, usa http://localhost:8100; no ar, "" quer dizer
     "no mesmo endereço do site". Se a API ficar em outro endereço, escreva ele aqui, ex.: "https://api.seudominio.com.br". */
  api: (function () {
    var l = window.location;
    return l.protocol === "file:" || (/^(localhost|127\.0\.0\.1)$/.test(l.hostname) && l.port !== "8100") ? "http://localhost:8100" : "";
  })(),
  loja: {
    ativa: true,                 /* false esconde carrinho e login e deixa só o catálogo com "Consultar este kit" */
    mostrarLoginSocialSemChave: true  /* Google/Facebook sem chave configurada na API aparecem apagados, com "em breve". false = somem */
  },

  /* Tela de abertura (vídeo). Toca uma vez por visita. Use ?semabertura na URL para pular durante testes.
     fadeEmSegundos: quando a abertura se dissolve na página (o vídeo termina em branco perto de 7,2 s; a música some junto).
     som: tenta tocar com a música do vídeo. Os navegadores bloqueiam som automático em boa parte das visitas: nesses casos
     o vídeo toca mudo e aparece o botão "Ativar som". false = sempre mudo e sem o botão. */
  abertura: { ativa: true, fadeEmSegundos: 7.2, som: true }
};
