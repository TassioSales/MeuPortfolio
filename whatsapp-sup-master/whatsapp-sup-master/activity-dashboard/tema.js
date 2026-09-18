/**
 * Tema claro/escuro do painel.
 *
 * Carregado no <head>, SEM `defer`, de propósito: ele estampa `data-theme` no
 * <html> antes do primeiro paint. Com `defer` (ou no fim do body) a tela
 * apareceria clara e viraria escura um quadro depois, em quem escolheu escuro —
 * o "flash" que todo painel com tema salvo erra na primeira versão.
 *
 * Arquivo próprio em vez de <script> inline pelo mesmo motivo que no editor-bio:
 * um dia o painel pode ganhar Content-Security-Policy, e `script-src 'self'`
 * mata script inline. Hash resolveria e quebraria em silêncio na primeira
 * edição do script.
 *
 * Por que `localStorage` aqui, quando o painel deixou de usar localStorage
 * para tudo o mais: as configurações do painel (nome, rótulos, assuntos) foram
 * para o banco porque são COMPARTILHADAS — o que um atendente renomeia, todos
 * precisam ver. Tema é o oposto: é preferência de quem está olhando, muda com o
 * monitor e com a hora do dia, e gravá-la no banco imporia a escolha de um a
 * toda a equipe. Fica no navegador porque é onde ela pertence.
 */
(function () {
  'use strict';

  // 'light' e 'dark' em inglês, e não 'claro'/'escuro': é o valor que vai para
  // o seletor CSS `:root[data-theme="dark"]`, é a mesma convenção do
  // editor-bio, e é o mesmo vocabulário de `prefers-color-scheme`. Traduzir
  // criaria uma tabela de conversão entre três lugares para não ganhar nada.
  var CHAVE = 'painel-tema';
  var ESCURO = 'dark';
  var CLARO = 'light';

  var raiz = document.documentElement;
  var ouvintes = [];

  /**
   * Todo acesso ao localStorage vai por aqui porque ele LANÇA, e não devolve
   * null, quando o navegador bloqueia armazenamento de site (janela privada com
   * cookies de terceiros barrados, política corporativa). Um throw aqui, no
   * <head> e antes do paint, deixaria a página em branco.
   */
  function lerEscolha() {
    try {
      var v = localStorage.getItem(CHAVE);
      return v === CLARO || v === ESCURO ? v : null;
    } catch (e) {
      return null;
    }
  }

  function gravarEscolha(valor) {
    try {
      if (valor === null) localStorage.removeItem(CHAVE);
      else localStorage.setItem(CHAVE, valor);
    } catch (e) {
      // Sem persistência a troca ainda vale para esta aba. Melhor que nada, e
      // não há nada a avisar: ninguém pode consertar isso da tela do painel.
    }
  }

  function doSistema() {
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches
      ? ESCURO
      : CLARO;
  }

  function estampar(tema) {
    raiz.setAttribute('data-theme', tema);
  }

  // A estampa acontece AQUI, no carregamento, e não em algum `DOMContentLoaded`:
  // é o que garante que ela venha antes do paint.
  estampar(lerEscolha() || doSistema());

  /* Enquanto NÃO houver escolha explícita, o painel acompanha o sistema ao
     vivo - alguém que troca o Windows para escuro às 18h vê o painel trocar
     junto, sem recarregar. Depois de escolher, a escolha manda e o sistema
     deixa de ter voz. */
  if (window.matchMedia) {
    var consulta = window.matchMedia('(prefers-color-scheme: dark)');
    var reagir = function () {
      if (lerEscolha() !== null) return;
      estampar(doSistema());
      avisar();
    };
    if (consulta.addEventListener) consulta.addEventListener('change', reagir);
    else if (consulta.addListener) consulta.addListener(reagir);
  }

  function avisar() {
    for (var i = 0; i < ouvintes.length; i++) {
      try {
        ouvintes[i](raiz.getAttribute('data-theme'));
      } catch (e) {
        /* ouvinte quebrado não derruba os outros */
      }
    }
  }

  window.PainelTema = {
    /** O tema que está na tela: sempre 'light' ou 'dark', nunca nulo. */
    aplicado: function () {
      return raiz.getAttribute('data-theme') === ESCURO ? ESCURO : CLARO;
    },

    /** O que a pessoa escolheu, ou `null` se ela está seguindo o sistema. */
    escolhido: lerEscolha,

    /** Passe `null` para voltar a seguir o sistema. */
    definir: function (tema) {
      var valor = tema === CLARO || tema === ESCURO ? tema : null;
      gravarEscolha(valor);
      estampar(valor || doSistema());
      avisar();
    },

    alternar: function () {
      this.definir(this.aplicado() === ESCURO ? CLARO : ESCURO);
      return this.aplicado();
    },

    /** Chamado a cada troca, inclusive as que vêm do sistema. */
    aoMudar: function (cb) {
      if (typeof cb === 'function') ouvintes.push(cb);
    },
  };
})();
