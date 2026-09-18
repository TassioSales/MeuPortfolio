/* Board de atividades — render, filtros, arrastar-e-soltar e painel de detalhes. */

(function () {
  'use strict';

  // NADA é guardado no navegador.
  //
  // Até aqui, `project` (nome, sigla, período) vivia no `localStorage`, sob uma
  // chave versionada — e a versão precisou subir duas vezes, porque um blob
  // salvo em cima de uma tela que mudou traz de volta um quadro que já não
  // existe. A segunda vez apagou as colunas novas.
  //
  // Com a configuração no banco (`GET/PATCH /internal/configuracao`) o problema
  // inteiro desaparece: não há foto local para envelhecer, e dois atendentes na
  // mesma instalação passam a ver a MESMA configuração. Era a última coisa
  // ajustável na tela que cada navegador guardava só para si.
  //
  // O que ainda usa `localStorage` é só o token e a preferência de aviso, em
  // api.js — credencial e conforto, nenhum dos dois compartilhável.

  // Limpeza de uma vez: o navegador de quem já usou o painel guarda as chaves
  // antigas, e nada mais as lê. Deixá-las ali não quebra nada hoje, mas é a
  // pista falsa que faz alguém depurar a configuração no lugar errado daqui a
  // seis meses.
  ['painel-chamados.v1', 'painel-chamados.v2'].forEach((chave) => {
    try {
      localStorage.removeItem(chave);
    } catch (e) {
      /* modo privado ou storage bloqueado: não havia o que limpar */
    }
  });

  // Estado de trabalho.
  //
  // O padrão do `data.js`, e nada mais. Quem escreve por cima é
  // `carregarConfiguracao()`, na primeira carga, com o que veio do banco -
  // antes havia aqui um terceiro objeto (`loadState()`) com a foto guardada no
  // navegador, e era ela que envelhecia e trazia telas antigas de volta.
  const state = Object.assign(JSON.parse(JSON.stringify(window.BOARD_DATA)), { issues: [] });
  const { project, columns } = state;
  const issues = state.issues;

  // `people` saiu do `state`: a lista mora no banco (GET /internal/pessoas) e é
  // COMPARTILHADA. Antes cada navegador tinha a sua no localStorage, e o
  // cadastro que você fazia aqui ninguém mais via.
  //
  // Reatribuídas a cada carga, por isso `let` e não `const`.
  let people = [];
  let peopleById = {};
  const columnsById = indexById(columns);

  /**
   * Os filtros de campo. Cada um corresponde a uma COLUNA de `Chamado`, e é o que
   * separa os cinco de verdade dos dois que sobraram do quadro genérico.
   *
   *   - `categoria`, `setor`, `tipo`, `prioridade`, `assignee` (responsável):
   *     existem no banco e filtram de verdade.
   *   - `type`: sobrou do quadro genérico, o elemento está oculto no HTML, e
   *     continua aqui só porque `clear-filters` o referencia.
   *
   * Havia um sexto, `epic` (área), que saiu de vez: ÁREA e SETOR eram o mesmo
   * conceito, e o filtro de setor é o que ficou.
   *
   * Convenção comum a todos: 'all' = sem filtro; 'none' = só os que NÃO têm o
   * campo preenchido — que é uma pergunta real numa fila de suporte ("o que
   * ninguém classificou ainda"); qualquer outro valor = o id ou o valor do enum.
   */
  const EMPTY_FILTERS = {
    text: '',
    assignee: null,
    type: 'all',
    categoria: 'all',
    setor: 'all',
    tipo: 'all',
    prioridade: 'all',
  };
  let filters = { ...EMPTY_FILTERS };

  /**
   * A árvore de assuntos, como veio de /internal/categorias.
   *
   * Fica em memória e é a ÚNICA fonte de rótulo no quadro: o cartão guarda só
   * `categoriaId`, e o texto é resolvido aqui. Guardar o rótulo dentro do cartão
   * faria uma renomeação no painel deixar cartões antigos com o nome velho até
   * alguém recarregar.
   */
  let assuntos = [];
  let assuntosPorId = {};

  /**
   * A lista de setores, como veio de /internal/setores.
   *
   * Mesmo desenho dos assuntos e pelo mesmo motivo: o cartão guarda só `setorId`,
   * e o nome é resolvido aqui. Guardar o nome dentro do cartão faria uma
   * renomeação no painel deixar cartões antigos com o nome velho até alguém
   * recarregar a página.
   */
  let setores = [];
  let setoresPorId = {};

  /**
   * As listas fixas (tipo, prioridade, canal, impacto...), de data.js.
   *
   * Ficam lá e não aqui porque são CONFIGURAÇÃO — o par valor-do-banco/texto-de-
   * tela —, e este arquivo é comportamento. A chave de cada item é literalmente o
   * valor do enum no Prisma, então não existe tabela de conversão em lugar nenhum.
   */
  const listas = state.listas || {};

  /* ---------- Ícones (inline, sem dependências) ----------------------- */

  const ICONS = {
    story: '<svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true">' +
      '<rect width="16" height="16" rx="2" fill="#36B37E"/>' +
      '<path d="M5 4.6h6a.4.4 0 0 1 .4.4v6.6L8 9.7l-3.4 1.9V5a.4.4 0 0 1 .4-.4z" fill="#fff"/></svg>',
    task: '<svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true">' +
      '<rect width="16" height="16" rx="2" fill="#4BADE8"/>' +
      '<path d="M6.8 10.4 4.6 8.2l.9-.9 1.3 1.3 3.7-3.7.9.9z" fill="#fff"/></svg>',
    bug: '<svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true">' +
      '<rect width="16" height="16" rx="2" fill="#E5493A"/>' +
      '<circle cx="8" cy="8" r="3.4" fill="#fff"/></svg>',
  };

  // O marcador do lado automático da conversa. Inline como os outros ícones:
  // este painel não carrega dependência nenhuma, nem de fonte de ícone.
  const ICONE_BOT =
    '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" ' +
    'stroke-width="2.5" stroke-linecap="round" aria-hidden="true">' +
    '<rect x="4" y="8" width="16" height="12" rx="2"/><path d="M12 4v4"/>' +
    '<path d="M9 13h.01M15 13h.01"/></svg>';

  /* ---------- Helpers ------------------------------------------------- */

  const ESCAPE_MAP = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };

  function indexById(list) {
    return list.reduce((acc, item) => {
      acc[item.id] = item;
      return acc;
    }, {});
  }

  function esc(str) {
    return String(str).replace(/[&<>"']/g, (c) => ESCAPE_MAP[c]);
  }

  function initials(name) {
    const parts = name.trim().split(/\s+/);
    if (!parts[0]) return '?';
    const last = parts.length > 1 ? parts[parts.length - 1][0] : '';
    return (parts[0][0] + last).toUpperCase();
  }

  function avatar(person, extraClass) {
    const cls = extraClass || '';
    if (!person) {
      return `<span class="avatar avatar--vazio ${cls}" title="Sem responsável">?</span>`;
    }
    return `<span class="avatar ${cls}" style="background:${esc(person.color)}" ` +
      `title="${esc(person.name)}">${esc(initials(person.name))}</span>`;
  }

  function byId(id) {
    return document.getElementById(id);
  }

  function findIssue(key) {
    return issues.find((issue) => issue.key === key);
  }

  /* ---------- Formatação de chamado ----------------------------------- */

  const MINUTO = 60 * 1000;
  const HORA = 60 * MINUTO;
  const DIA = 24 * HORA;

  /** "12 min", "3 h", "5 d" — quanto tempo o chamado está aberto. */
  function idadeCurta(iso) {
    const ms = Date.now() - new Date(iso).getTime();
    if (!Number.isFinite(ms) || ms < 0) return '—';
    if (ms < HORA) return Math.floor(ms / MINUTO) + ' min';
    if (ms < DIA) return Math.floor(ms / HORA) + ' h';
    return Math.floor(ms / DIA) + ' d';
  }

  function dataLonga(iso) {
    const d = new Date(iso);
    return Number.isNaN(d.getTime()) ? '—' : d.toLocaleString('pt-BR');
  }

  /**
   * A partir de quando um chamado 'aberto' sem 1º atendimento entra em
   * "Atenção necessária". Único lugar que define isto — mude só aqui.
   *
   * Não existe "prioridade" nem "SLA" configurado no banco (ver Chamado em
   * prisma/schema.prisma): o critério é só TEMPO DE ESPERA sobre dado real
   * (`dataAbertura`), não uma classificação inventada no cliente.
   */
  const LIMIAR_ATENCAO_MS = 4 * HORA;

  function precisaAtencao(issue) {
    return issue.status === 'aberto' &&
      !issue.primeiroAtendimentoEm &&
      (Date.now() - new Date(issue.abertoEm).getTime()) > LIMIAR_ATENCAO_MS;
  }

  /**
   * Paleta de identidade das bolhas — a MESMA em três lugares: aqui (para quem
   * abriu o chamado, que não tem cadastro), em `PERSON_COLORS` (a cor sugerida
   * ao criar pessoa na tela) e em `CORES` no `src/internal/pessoas.ts` (a cor
   * de quem nasce de um login pelo Entra). Trocar em um só deixaria a mesma
   * equipe pintada por duas paletas.
   *
   * OITO cores, e não dez: com dez, o par de vizinhos mais próximo ficava a
   * ΔE 4,8 sob deuteranopia — duas pessoas cadastradas em seguida com a mesma
   * cor para quem não distingue vermelho de verde. Com oito, o pior par sobe
   * para 11,9 (medido, `scripts/validate_palette.js` da skill dataviz). Oito
   * cores para uma equipe maior que oito significa repetição, e repetição aqui
   * é inofensiva: as INICIAIS estão escritas dentro da bolha e o nome inteiro
   * no `title` — a cor é auxílio de memória, não a identidade.
   *
   * Todas escuras o suficiente para texto branco por cima (6,3:1 a 9,2:1), o
   * que as faz funcionar sobre cartão claro E sobre cartão escuro — por isso
   * elas não mudam com o tema.
   */
  const CORES_SOLICITANTE = [
    '#96421C', '#4C3BA8', '#8A5000', '#3B3F8F',
    '#3D6B33', '#5E4B8B', '#7A3E12', '#0F6068',
  ];

  /** Cor estável por nome: o mesmo solicitante recebe sempre a mesma. */
  function corDoNome(nome) {
    let soma = 0;
    for (let i = 0; i < nome.length; i++) soma = (soma + nome.charCodeAt(i)) % 9973;
    return CORES_SOLICITANTE[soma % CORES_SOLICITANTE.length];
  }

  function avatarSolicitante(nome, extraClass) {
    const limpo = (nome || '').trim();
    const cls = extraClass || '';
    if (!limpo) {
      return '<span class="avatar avatar--vazio ' + cls + '">?</span>';
    }
    return '<span class="avatar ' + cls + '" style="background:' + corDoNome(limpo) + '" ' +
      'title="' + esc(limpo) + '">' + esc(initials(limpo)) + '</span>';
  }

  function nomeColuna(id) {
    return columnsById[id] ? columnsById[id].name : id;
  }

  /* ---------- Listas fixas (enums) ------------------------------------- */

  /**
   * O texto de tela de um valor de enum, ou o próprio valor se a lista não o
   * conhece.
   *
   * O fallback importa: se uma migração acrescentar um valor ao enum e ninguém
   * atualizar data.js, o quadro mostra `loja_fechada` em vez de apagar o campo -
   * feio, mas verdadeiro, e visível o bastante para alguém corrigir.
   */
  function rotuloLista(nome, valor) {
    if (!valor) return null;
    const item = (listas[nome] || []).find((x) => x.id === valor);
    return item ? item.name : valor;
  }

  function opcoesLista(nome, selecionado, rotuloVazio) {
    const vazio = rotuloVazio
      ? '<option value=""' + (!selecionado ? ' selected' : '') + '>' + esc(rotuloVazio) +
        '</option>'
      : '';
    return vazio + (listas[nome] || []).map((x) =>
      '<option value="' + esc(x.id) + '"' + (x.id === selecionado ? ' selected' : '') + '>' +
      esc(x.name) + '</option>'
    ).join('');
  }

  function preencherSelectLista(sel, nome, selecionado, rotuloVazio) {
    if (!sel) return;
    sel.innerHTML = opcoesLista(nome, selecionado, rotuloVazio);
  }

  /* ---------- Setores -------------------------------------------------- */

  function ordenarSetores(lista) {
    // Mesmo desempate da rota: `ordem` empata com frequência, e sem o segundo
    // critério a lista trocaria de ordem entre duas cargas sem nada ter mudado.
    return lista.slice().sort((a, b) =>
      a.ordem - b.ordem || a.nome.localeCompare(b.nome, 'pt-BR') || a.id - b.id
    );
  }

  function nomeSetor(id) {
    const s = setoresPorId[id];
    return s ? s.nome : null;
  }

  /**
   * Preenche um seletor de setor.
   *
   * `somenteAtivos` esconde os desativados — EXCETO o que já está selecionado,
   * pela mesma razão do seletor de assunto: um chamado classificado num setor que
   * saiu de circulação apareceria como "Sem setor", e o primeiro salvamento
   * apagaria a classificação sem ninguém ter pedido.
   */
  function preencherSelectSetor(sel, selecionadoId, somenteAtivos) {
    if (!sel) return;
    const linhas = ordenarSetores(setores).filter(
      (x) => !somenteAtivos || x.ativo || x.id === selecionadoId
    );

    sel.innerHTML =
      '<option value=""' + (!selecionadoId ? ' selected' : '') + '>Sem setor</option>' +
      linhas.map((x) =>
        '<option value="' + x.id + '"' + (x.id === selecionadoId ? ' selected' : '') + '>' +
        esc(x.nome) + (x.ativo ? '' : ' (inativo)') + '</option>'
      ).join('');
  }

  function renderFiltroSetor() {
    const sel = byId('filter-setor');
    if (!sel) return;

    sel.innerHTML =
      '<option value="all">Setor</option>' +
      '<option value="none">Sem setor</option>' +
      ordenarSetores(setores).map((x) =>
        '<option value="' + x.id + '">' + esc(x.nome) + '</option>'
      ).join('');

    // A escolha só sobrevive se o setor ainda existir: um filtro apontando para
    // um id apagado esconderia todos os cartões sem explicar por quê.
    const validos = ['all', 'none'].concat(setores.map((x) => String(x.id)));
    sel.value = validos.indexOf(filters.setor) > -1 ? filters.setor : 'all';
    filters.setor = sel.value;
  }

  async function carregarSetores(opcoes) {
    if (!PainelApi.temToken()) return;
    try {
      const r = await PainelApi.listarSetores();
      setores = r.setores;
      setoresPorId = indexById(setores);
      renderFiltroSetor();
    } catch (err) {
      // Igual aos assuntos: sem a lista o quadro continua utilizável, só sem o
      // nome do setor nos cartões. Avisa e segue, em vez de derrubar a carga.
      if (!(opcoes && opcoes.silencioso)) {
        showToast('Não foi possível carregar os setores: ' + err.message);
      }
    }
  }

  /** Seletor de responsável, a partir do cadastro de pessoas já carregado. */
  function preencherSelectPessoa(sel, selecionadoId) {
    if (!sel) return;
    sel.innerHTML =
      '<option value=""' + (!selecionadoId ? ' selected' : '') + '>Sem responsável</option>' +
      people.map((pp) =>
        '<option value="' + pp.id + '"' + (pp.id === selecionadoId ? ' selected' : '') + '>' +
        esc(pp.name || '(sem nome)') + '</option>'
      ).join('');
  }

  /* ---------- Prazo (SLA) ---------------------------------------------- */

  /**
   * Como o prazo aparece: quanto falta, ou quanto passou.
   *
   * O prazo de um chamado JÁ CONCLUÍDO não conta mais o relógio - ele é lido
   * contra a data de conclusão, e não contra agora. Sem isso, um chamado
   * entregue no prazo em março apareceria hoje como "atrasado 5 meses", que é
   * uma afirmação falsa sobre um trabalho que foi feito a tempo.
   */
  function estadoPrazo(issue) {
    if (!issue.prazoEm) return null;

    const prazo = new Date(issue.prazoEm).getTime();
    if (!Number.isFinite(prazo)) return null;

    const referencia = issue.resolvidoEm ? new Date(issue.resolvidoEm).getTime() : Date.now();
    const restante = prazo - referencia;
    const concluido = !!issue.resolvidoEm;

    if (restante < 0) {
      return {
        classe: concluido ? 'is-estourado' : 'is-atrasado',
        texto: (concluido ? 'fora do prazo ' : 'atrasado ') + duracaoCurta(-restante),
        titulo: 'Prazo: ' + dataLonga(issue.prazoEm),
      };
    }

    return {
      classe: concluido ? 'is-no-prazo' : restante < DIA ? 'is-perto' : '',
      texto: (concluido ? 'no prazo' : 'vence em ' + duracaoCurta(restante)),
      titulo: 'Prazo: ' + dataLonga(issue.prazoEm),
    };
  }

  /** "2 h 30" a partir de minutos, para os campos de tempo estimado x gasto. */
  function minutosLegiveis(min) {
    if (min === null || min === undefined) return '—';
    if (min < 60) return min + ' min';
    const h = Math.floor(min / 60);
    const m = min % 60;
    return h + ' h' + (m ? ' ' + m + ' min' : '');
  }

  /** Centavos para "R$ 1.234,56". */
  function reais(centavos) {
    if (centavos === null || centavos === undefined) return '—';
    return (centavos / 100).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
  }

  /** "1 h", "3,5 h", "2,1 d" — duração vinda das métricas, que chega em minutos. */
  function duracaoMin(minutos) {
    if (minutos === null || minutos === undefined) return '—';
    if (minutos < 60) return Math.round(minutos) + ' min';
    if (minutos < 60 * 24) return Math.round(minutos / 6) / 10 + ' h';
    return Math.round(minutos / 144) / 10 + ' d';
  }

  /* ---------- Árvore de assuntos --------------------------------------- */

  // Mesmo teto do servidor. Uma árvore mais funda que isto não é menu de
  // atendimento; e o teto também impede que um ciclo gravado por fora da API
  // (SQL crua no arquivo do banco) trave o navegador num laço.
  const MAX_PROFUNDIDADE = 10;

  function ordenarAssuntos(lista) {
    // `ordem` empata com frequência, e o desempate por `id` é o mesmo do menu do
    // WhatsApp: sem ele, a lista aqui e a numeração lá poderiam discordar.
    return lista.slice().sort((a, b) => a.ordem - b.ordem || a.id - b.id);
  }

  /** Raízes primeiro, cada uma seguida das próprias filhas, com o nível junto. */
  function assuntosEmArvore() {
    const saida = [];

    const descer = (paiId, nivel) => {
      if (nivel >= MAX_PROFUNDIDADE) return;
      const filhas = ordenarAssuntos(assuntos.filter((a) => (a.paiId || null) === paiId));
      filhas.forEach((a) => {
        saida.push({ assunto: a, nivel: nivel });
        descer(a.id, nivel + 1);
      });
    };

    descer(null, 0);
    return saida;
  }

  /** "SUPORTE AO SISTEMA VETOR / FISCAL" — o mesmo caminho que a conversa mostra. */
  function caminhoAssunto(id) {
    const partes = [];
    let atual = assuntosPorId[id];
    for (let i = 0; i < MAX_PROFUNDIDADE && atual; i++) {
      partes.unshift(atual.rotulo);
      atual = atual.paiId ? assuntosPorId[atual.paiId] : null;
    }
    return partes.join(' / ');
  }

  /**
   * O assunto está fora do menu do WhatsApp — por marcação própria ou herdada.
   *
   * Herdada porque a conversa desce um nível por vez: um assunto guarda-chuva
   * marcado como interno nunca é oferecido, então nenhuma filha dele chega a ser
   * ofertada, por mais que a coluna `visivelNoWhatsapp` da filha diga `true`.
   *
   * O servidor NÃO reescreve a coluna das filhas quando o pai vira interno, e é
   * de propósito: religar o pai devolve o ramo exatamente como estava, sem
   * ninguém ter de lembrar quais filhas eram internas antes. O preço é este
   * cálculo aqui — o painel precisa dizer a verdade na tela, senão a linha da
   * filha mostraria "no WhatsApp" para um assunto que ninguém alcança.
   *
   * Devolve `'proprio'`, `'herdado'` ou `''` (está no menu), porque a linha
   * mostra as duas situações de formas diferentes: a própria tem interruptor, a
   * herdada tem explicação.
   */
  function foraDoMenu(assunto) {
    if (!assunto) return '';
    if (assunto.visivelNoWhatsapp === false) return 'proprio';

    let atual = assunto.paiId ? assuntosPorId[assunto.paiId] : null;
    for (let i = 0; i < MAX_PROFUNDIDADE && atual; i++) {
      if (atual.visivelNoWhatsapp === false) return 'herdado';
      atual = atual.paiId ? assuntosPorId[atual.paiId] : null;
    }
    return '';
  }

  /** O próprio nó e tudo abaixo dele: os pais que criariam ciclo. */
  function descendentesDe(id) {
    if (id === null || id === undefined) return [];
    const saida = [id];
    for (let i = 0; i < saida.length; i++) {
      assuntos.forEach((a) => {
        if (a.paiId === saida[i] && saida.indexOf(a.id) === -1) saida.push(a.id);
      });
    }
    return saida;
  }

  /**
   * O sufixo de um assunto dentro de um `<option>`.
   *
   * `<option>` não aceita marcação, então o aviso tem de caber no texto — e é
   * ele que faz o atendente perceber, ao classificar um chamado à mão, que
   * aquele assunto nunca foi oferecido ao cliente.
   *
   * Os dois estados se excluem, e a precedência é a útil: um assunto inativo não
   * é escolhível em lugar nenhum, e chamá-lo de "interno" sugeriria o contrário.
   */
  function marcaDoAssunto(a) {
    if (!a.ativa) return ' (inativo)';
    return foraDoMenu(a) ? ' (interno)' : '';
  }

  function opcaoAssunto(no, selecionadoId) {
    const a = no.assunto;
    // NBSP porque o navegador colapsa espaço comum dentro de <option>, e o recuo
    // é o que mostra que o assunto é um sub-assunto e não uma raiz.
    const recuo = new Array(no.nivel + 1).join('   ');
    return '<option value="' + a.id + '"' + (a.id === selecionadoId ? ' selected' : '') + '>' +
      recuo + esc(a.rotulo) + marcaDoAssunto(a) + '</option>';
  }

  /**
   * Preenche um seletor de assunto.
   *
   * `somenteAtivos` esconde os desativados — EXCETO o que já está selecionado.
   * Sem essa exceção, um chamado classificado num assunto que saiu de circulação
   * apareceria como "Sem assunto" no seletor, e o primeiro salvamento apagaria a
   * classificação sem ninguém ter pedido.
   */
  function preencherSelectAssunto(sel, selecionadoId, somenteAtivos) {
    if (!sel) return;
    const linhas = assuntosEmArvore().filter(
      (n) => !somenteAtivos || n.assunto.ativa || n.assunto.id === selecionadoId
    );

    sel.innerHTML =
      '<option value=""' + (!selecionadoId ? ' selected' : '') + '>Sem assunto</option>' +
      linhas.map((n) => opcaoAssunto(n, selecionadoId)).join('');
  }

  function renderFiltroAssunto() {
    const sel = byId('filter-categoria');
    if (!sel) return;

    sel.innerHTML =
      '<option value="all">Assunto</option>' +
      '<option value="none">Sem assunto</option>' +
      assuntosEmArvore().map((n) => opcaoAssunto(n, null)).join('');

    // A escolha só sobrevive se o assunto ainda existir: um filtro apontando para
    // um id apagado esconderia todos os cartões sem explicar por quê.
    const validos = ['all', 'none'].concat(assuntos.map((a) => String(a.id)));
    sel.value = validos.indexOf(filters.categoria) > -1 ? filters.categoria : 'all';
    filters.categoria = sel.value;
  }

  async function carregarAssuntos(opcoes) {
    if (!PainelApi.temToken()) return;
    try {
      const r = await PainelApi.listarAssuntos();
      assuntos = r.categorias;
      assuntosPorId = indexById(assuntos);
      renderFiltroAssunto();
    } catch (err) {
      // Sem a árvore o quadro continua utilizável: os cartões aparecem, só sem
      // rótulo de assunto. Por isso isto avisa e segue, em vez de derrubar a
      // carga inteira.
      if (!(opcoes && opcoes.silencioso)) {
        showToast('Não foi possível carregar os assuntos: ' + err.message);
      }
    }
  }

  /**
   * Traz o cadastro de pessoas do banco.
   *
   * O servidor fala `nome`/`cor`, o quadro fala `name`/`color`: a tradução é
   * aqui e só aqui. O `id` fica NUMÉRICO, como veio - a busca por
   * `dataset.person` continua funcionando porque chave de objeto é sempre
   * string, e é o mesmo número que as rotas PATCH e DELETE esperam de volta.
   */
  async function carregarPessoas(opcoes) {
    if (!PainelApi.temToken()) return;
    try {
      const r = await PainelApi.listarPessoas();
      people = r.pessoas.map((p) => ({ id: p.id, name: p.nome, color: p.cor }));
      peopleById = indexById(people);
      renderAvatarGroup();
    } catch (err) {
      // Igual aos assuntos: sem a lista o quadro continua utilizável, só sem as
      // bolhas. Avisa e segue, em vez de derrubar a carga inteira.
      if (!(opcoes && opcoes.silencioso)) {
        showToast('Não foi possível carregar as pessoas: ' + err.message);
      }
    }
  }

  /**
   * A bolha do canto superior direito: quem está logado.
   *
   * Os dados vêm de `/painel-servidor.js`, gerado pelo servidor a partir do
   * cookie de sessão - o navegador nunca recebeu token nenhum do Entra, só o
   * nome e o e-mail de quem já está olhando a própria tela.
   *
   * As iniciais saem do mesmo `initials()` das outras bolhas, e a cor do mesmo
   * `corDoNome()` do avatar do solicitante: uma pessoa tem a mesma cor em toda
   * a tela, e ninguém precisa escolher cor nenhuma.
   *
   * Sem login configurado, a bolha fica exatamente como está no HTML.
   */
  function renderConta() {
    const el = byId('conta-avatar');
    const login = (window.PAINEL_SERVIDOR && window.PAINEL_SERVIDOR.login) || {};
    if (!el || !login.ativo) return;

    const nome = login.nome || login.email || '';

    el.textContent = initials(nome);
    el.style.background = corDoNome(nome || '?');
    el.title = login.email && login.email !== nome ? nome + ' (' + login.email + ')' : nome;
    el.setAttribute('aria-label', 'Conta de ' + nome + ' — sair');

    // Sem isto o clique cairia no aviso genérico de "em breve" (o handler de
    // `[data-soon]`), que agora seria mentira: a bolha faz alguma coisa.
    el.removeAttribute('data-soon');

    el.addEventListener('click', () => {
      if (!window.confirm('Sair da conta ' + (login.email || nome) + '?')) return;
      // `/auth/sair` encerra aqui E na Microsoft. Só apagar o cookie daqui
      // deixaria o próximo login entrar sem pedir nada.
      window.location.href = '/auth/sair';
    });
  }

  /* ---------- Filtros ------------------------------------------------- */

  /**
   * A mesma pergunta para cinco campos: 'all' passa tudo, 'none' passa só o que
   * está vazio, e qualquer outro valor compara como texto.
   *
   * Comparar como TEXTO é o que faz a função servir id numérico (setor,
   * categoria, responsável) e valor de enum (tipo, prioridade) sem dois ramos: o
   * valor do `<select>` é sempre string, e converter para número daria `NaN` em
   * 'interno'.
   */
  function passaFiltro(escolha, valor) {
    if (escolha === 'all') return true;
    if (escolha === 'none') return valor === null || valor === undefined;
    return String(valor) === String(escolha);
  }

  function matches(issue) {
    if (filters.text) {
      // Busca por número (#12), por resumo, por solicitante, pelo texto da
      // descrição — que é onde costuma estar a palavra que a pessoa lembra — e
      // pelas etiquetas, que existem justamente para serem procuradas. A unidade
      // da franquia entra também: "quais chamados são da loja 42" é uma pergunta
      // que se faz digitando o código, não abrindo um filtro.
      const haystack = (issue.key + ' ' + issue.title + ' ' + issue.solicitante +
        ' ' + issue.descricao + ' ' + (issue.tags || []).join(' ') +
        ' ' + (issue.franquiaCodigo || '') + ' ' + (issue.franquiaNome || '')).toLowerCase();
      if (haystack.indexOf(filters.text) === -1) return false;
    }

    if (!passaFiltro(filters.categoria, issue.categoriaId)) return false;
    if (!passaFiltro(filters.setor, issue.setorId)) return false;
    if (!passaFiltro(filters.tipo, issue.tipo)) return false;
    if (!passaFiltro(filters.prioridade, issue.prioridade)) return false;

    // O responsável não vem de um `<select>`: são as bolhas de perfil, que
    // guardam `null` quando nenhuma está ativa (e não 'all').
    if (filters.assignee !== null && String(issue.responsavelId) !== filters.assignee) {
      return false;
    }

    return true;
  }

  /* ---------- Render -------------------------------------------------- */

  // As situações em que o chamado não está mais em trabalho. `fechado` entrou
  // junto com a coluna: ele é encerramento, e um cartão fechado desenhado como
  // ativo faria a coluna parecer fila.
  const ENCERRADAS = ['resolvido', 'fechado', 'cancelado'];

  /**
   * O cartão mostra o que um chamado realmente tem — e agora tem bastante.
   *
   * O que entrou com a classificação, e por quê:
   *   - a PRIORIDADE como faixa de cor na borda esquerda, e não como texto: é a
   *     informação que decide o que puxar primeiro, e ler quatro palavras em
   *     vinte cartões é mais lento que ver quatro cores;
   *   - o SETOR e o TIPO como etiquetas, porque são as duas perguntas que se faz
   *     olhando um quadro cheio ("isso é meu?", "isso é da rede?");
   *   - o PRAZO, que é a única informação do cartão que muda de cor sozinha:
   *     atrasado é vermelho, e a diferença entre "vence em 2 h" e "atrasado 2 h"
   *     é a decisão do dia;
   *   - o RESPONSÁVEL ao lado do solicitante. A bolha cinza com "?" é
   *     deliberada: chamado sem responsável precisa parecer incompleto.
   *
   * O que continua fora: story points, épico e contador de comentários. Os dois
   * primeiros não existem em `Chamado`, e o terceiro custaria carregar os
   * comentários de 500 cartões para escrever um número em cada.
   */
  function cardHtml(issue) {
    // `ENCERRADAS` e não a comparação inline: com `fechado` no enum, a lista é o
    // único lugar que define o que conta como encerrado.
    const encerrado = ENCERRADAS.indexOf(issue.status) > -1;
    // Reaproveita `.is-flagged` (herdado do template genérico, sem uso desde que
    // o botão de sinalizar saiu do detalhe): mesmo destaque visual, agora ligado
    // a um critério real — tempo de espera, não prioridade inventada.
    const atencao = precisaAtencao(issue);

    // Só a FOLHA do assunto, e não o caminho inteiro: o cartão é estreito, e o
    // caminho completo cabe no detalhe (fica no `title`).
    const assunto = issue.categoriaId ? assuntosPorId[issue.categoriaId] : null;
    const etiquetas = [];

    if (assunto) {
      etiquetas.push('<span class="tag tag--assunto" title="' +
        esc(caminhoAssunto(assunto.id)) + '">' + esc(assunto.rotulo) + '</span>');
    }

    const setor = nomeSetor(issue.setorId);
    if (setor) {
      etiquetas.push('<span class="tag tag--setor" title="Setor responsável">' +
        esc(setor) + '</span>');
    }

    if (issue.tipo) {
      etiquetas.push('<span class="tag tag--tipo tag--tipo-' + esc(issue.tipo) + '">' +
        esc(rotuloLista('tipo', issue.tipo)) + '</span>');
    }

    // Etiquetas livres depois das fixas: elas são as menos previsíveis, e vir por
    // último mantém as três primeiras posições estáveis entre cartões.
    (issue.tags || []).forEach((t) => {
      etiquetas.push('<span class="tag tag--livre">' + esc(t) + '</span>');
    });

    const rotulos = etiquetas.length
      ? '<div class="card__labels">' + etiquetas.join('') + '</div>'
      : '';

    const prazo = estadoPrazo(issue);
    const chipPrazo = prazo
      ? '<span class="card__prazo ' + prazo.classe + '" title="' + esc(prazo.titulo) + '">' +
        esc(prazo.texto) + '</span>'
      : '';

    // Três sinais que não se atropelam: a BORDA é da prioridade, o CHIP é do
    // prazo, e o FUNDO é da espera pelo 1º atendimento (`is-atencao`). Um
    // chamado sem prazo definido não tem chip nenhum — é justamente ele que o
    // fundo âmbar continua encontrando.
    return '<article class="card card--prio-' + esc(issue.prioridade || 'media') +
      (encerrado ? ' is-done' : '') + (atencao ? ' is-atencao' : '') + '" draggable="true" ' +
      'tabindex="0" data-key="' + esc(issue.key) + '">' +
      rotulos +
      '<div class="card__title">' + esc(issue.title) + '</div>' +
      '<div class="card__foot">' +
        '<span class="card__key">' + esc(issue.key) + '</span>' +
        '<span class="card__meta" title="Aberto em ' + esc(dataLonga(issue.abertoEm)) + '">' +
          esc(idadeCurta(issue.abertoEm)) + '</span>' +
        chipPrazo +
        '<span class="card__foot-spacer"></span>' +
        // Duas bolhas, nesta ordem: quem PEDIU e quem ATENDE. O responsável fica
        // à direita, colado na borda, porque é a coluna que o olho percorre
        // procurando "o que é meu".
        avatarSolicitante(issue.solicitante, 'avatar--sm') +
        avatar(peopleById[issue.responsavelId], 'avatar--sm') +
      '</div>' +
    '</article>';
  }

  // Mensagem por coluna em vez do genérico "Nenhum chamado": cada coluna vazia
  // significa uma coisa diferente numa fila de suporte.
  // Uma entrada por valor do enum `Situacao`. Faltando alguma, a coluna cai no
  // genérico "Nenhum chamado" — foi o que aconteceu com `aguardando_resposta` e
  // `fechado` quando eles entraram no schema e este mapa ficou para trás.
  const COLUNA_VAZIA = {
    aberto: 'Tudo em dia — não há chamados aguardando atendimento.',
    em_andamento: 'Nada em andamento no momento.',
    aguardando_resposta: 'Ninguém esperando resposta do solicitante.',
    resolvido: 'Os chamados concluídos aparecem aqui.',
    fechado: 'Nenhum chamado fechado.',
    cancelado: 'Nenhum chamado cancelado.',
  };

  function columnHtml(col, visible) {
    const cards = visible.filter((issue) => issue.status === col.id);
    const overLimit = col.limit !== null && cards.length > col.limit;
    const limitLabel = col.limit !== null ? `<span class="column__limit">máx. ${col.limit}</span>` : '';
    const body = cards.length
      ? cards.map(cardHtml).join('')
      : '<div class="column__empty">' + esc(COLUNA_VAZIA[col.id] || 'Nenhum chamado') + '</div>';

    return `<section class="column${overLimit ? ' is-over-limit' : ''}" ` +
      `data-column="${col.id}" aria-label="${esc(col.name)}">` +
      '<header class="column__head">' +
        `<span class="column__title">${esc(col.name)}</span>` +
        `<span class="column__count">${cards.length}</span>` +
        limitLabel +
      '</header>' +
      `<div class="column__cards" data-drop="${col.id}">${body}</div>` +
    '</section>';
  }

  /** Texto de busca ou assunto escolhido: os dois filtros de campo reais. */
  function filtroAtivo() {
    return filters.text !== '' || filters.categoria !== 'all';
  }

  /**
   * Total / A fazer / Em andamento / Resolvidos, sobre TODOS os chamados
   * carregados — de propósito não usa `visible`: a faixa é o panorama geral,
   * não deve encolher só porque alguém digitou uma busca.
   */
  function renderKpiStrip() {
    const el = byId('kpi-strip');
    if (!el) return;

    // Uma chave por situação do enum, e não só as quatro de antes: com
    // `aguardando_resposta` e `fechado` de fora, a soma dos indicadores não
    // fechava com o Total, e um chamado podia estar em nenhum deles. Painel
    // cujos números não somam é painel em que ninguém confia.
    const porStatus = {
      aberto: 0,
      em_andamento: 0,
      aguardando_resposta: 0,
      resolvido: 0,
      fechado: 0,
      cancelado: 0,
    };
    issues.forEach((issue) => {
      if (porStatus[issue.status] !== undefined) porStatus[issue.status] += 1;
    });

    // "Concluídos" junta resolvido + fechado, igual ao Dashboard: as duas
    // views precisam contar do mesmo jeito, senão a comparação entre elas
    // levanta uma dúvida que não existe.
    el.innerHTML =
      kpiHtml(issues.length, 'Total') +
      kpiHtml(porStatus.aberto, 'A fazer') +
      kpiHtml(porStatus.em_andamento, 'Em andamento') +
      kpiHtml(porStatus.aguardando_resposta, 'Aguardando resposta') +
      kpiHtml(porStatus.resolvido + porStatus.fechado, 'Concluídos') +
      kpiHtml(porStatus.cancelado, 'Cancelados');
  }

  /** Mesmo critério real de `precisaAtencao`, também sobre todos os chamados. */
  function renderAtencao() {
    const el = byId('atencao-necessaria');
    if (!el) return;

    const alvo = issues.filter(precisaAtencao);
    if (alvo.length === 0) {
      el.hidden = true;
      return;
    }

    const horas = Math.round(LIMIAR_ATENCAO_MS / HORA);
    el.hidden = false;
    el.innerHTML = '<span class="atencao__icone" aria-hidden="true">⚠</span>' +
      '<span class="atencao__texto">' +
        (alvo.length === 1 ? '1 chamado aguardando' : alvo.length + ' chamados aguardando') +
        ' o 1º atendimento há mais de ' + horas + ' horas.' +
      '</span>';
  }

  function render() {
    const visible = issues.filter(matches);

    byId('board').innerHTML = columns.map((col) => columnHtml(col, visible)).join('');

    const contagem = byId('issue-count');
    if (visible.length === 0 && filtroAtivo()) {
      contagem.textContent = '0 chamados encontrados para os filtros selecionados';
    } else {
      contagem.textContent = visible.length + (visible.length === 1 ? ' chamado encontrado' : ' chamados encontrados');
    }

    renderKpiStrip();
    renderAtencao();
  }

  /* ---------- Modal de detalhes --------------------------------------- */

  let openModalKey = null;

  function optionsFor(items, selectedId, noneLabel) {
    const none = noneLabel
      ? `<option value=""${!selectedId ? ' selected' : ''}>${esc(noneLabel)}</option>`
      : '';
    return none + items.map((item) => {
      const label = item.name || item.label;
      return `<option value="${item.id}"${item.id === selectedId ? ' selected' : ''}>${esc(label)}</option>`;
    }).join('');
  }

  /** Duração absoluta, para os marcos de SLA. */
  function duracaoCurta(ms) {
    if (!Number.isFinite(ms)) return '—';
    if (ms < HORA) return Math.round(ms / MINUTO) + ' min';
    if (ms < DIA) return Math.round(ms / (HORA / 10)) / 10 + ' h';
    return Math.round(ms / (DIA / 10)) / 10 + ' d';
  }

  /**
   * Um marco de SLA: quando aconteceu, e quanto tempo depois da abertura.
   *
   * `null` é "ainda não aconteceu", e sai como texto e não como zero: um chamado
   * que ninguém pegou não foi atendido em 0 minutos.
   */
  function marcoSla(abertoEm, marco) {
    if (!marco) return '<span class="field-grid__fraco">— ainda não</span>';

    const ms = new Date(marco).getTime() - new Date(abertoEm).getTime();
    return esc(dataLonga(marco)) +
      ' <span class="field-grid__fraco">(' + esc(duracaoCurta(Math.max(0, ms))) +
      ' após a abertura)</span>';
  }

  /* ---------- Detalhe: campos, comentários, anexos, dependências ------- */

  /**
   * As listas que pendem do chamado ABERTO na tela.
   *
   * Fica fora do cartão de propósito: comentário, anexo e dependência não vêm na
   * listagem (seriam 500 cartões x N linhas para desenhar quatro campos), então
   * são buscadas ao abrir o modal e guardadas aqui até ele fechar.
   *
   * É o que permite `renderModal` redesenhar o modal inteiro a cada campo
   * alterado sem re-buscar nada: o redesenho lê daqui.
   */
  let detalhe = null;

  /** Texto de tela de cada campo, para a mensagem de confirmação e de erro. */
  const ROTULOS_CAMPO = {
    tipo: 'tipo',
    setorId: 'setor responsável',
    prioridade: 'prioridade',
    canal: 'canal de origem',
    contato: 'contato do solicitante',
    responsavelId: 'responsável',
    prazoEm: 'prazo',
    setorOrigemId: 'setor de origem',
    tipoSolicitacao: 'tipo de solicitação',
    impacto: 'impacto no negócio',
    sistemaAfetado: 'sistema afetado',
    tempoEstimadoMin: 'tempo estimado',
    tempoGastoMin: 'tempo gasto',
    franquiaCodigo: 'código da unidade',
    franquiaNome: 'nome da unidade',
    franqueadoNome: 'franqueado',
    franqueadoContato: 'contato do franqueado',
    localizacao: 'localização',
    tipoFranquia: 'tipo de chamado da franquia',
    afetaAtendimento: 'impacto no atendimento ao cliente',
    envolveCusto: 'envolve custo',
    valorEstimadoCentavos: 'valor estimado',
    precisaAprovacao: 'precisa de aprovação',
    urgenciaComercial: 'urgência comercial',
  };

  /* ---------- Conversão de data para o <input datetime-local> ---------- */

  /**
   * ISO em UTC -> "2026-08-31T14:30" no fuso de quem está olhando.
   *
   * O `datetime-local` não aceita offset e sempre fala no fuso do navegador, então
   * a conversão tem de ser feita à mão nas duas pontas. Mandar o ISO cru para o
   * campo faria um prazo de 14h em Brasília aparecer como 17h.
   */
  function paraDatetimeLocal(iso) {
    if (!iso) return '';
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return '';
    const pad = (n) => String(n).padStart(2, '0');
    return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()) +
      'T' + pad(d.getHours()) + ':' + pad(d.getMinutes());
  }

  /** A volta: o valor do campo é hora LOCAL, e o servidor quer ISO em UTC. */
  function deDatetimeLocal(valor) {
    if (!valor) return null;
    const d = new Date(valor);
    return Number.isNaN(d.getTime()) ? null : d.toISOString();
  }

  /* ---------- Gravação de um campo ------------------------------------- */

  /**
   * Altera UM campo de classificação e persiste.
   *
   * Mesmo desenho de `moverPara` e `classificar` - tela primeiro, desfaz se a API
   * recusar -, e pela mesma razão: numa fila de suporte o campo precisa responder
   * na hora, e a falha é o caso raro.
   *
   * A diferença é que aqui a resposta traz o chamado INTEIRO, e ela é aplicada
   * por cima do cartão em vez de o cartão ser remendado à mão. É o que mantém a
   * tela igual ao banco quando o servidor normaliza algo que a tela mandou - um
   * texto com espaços nas pontas, por exemplo, volta sem eles.
   *
   * Não existe botão "salvar". Cada campo grava ao sair dele, porque o modal não
   * é um formulário de criação: é a ficha de um chamado que já existe, e um botão
   * de salvar criaria o estado "mudei e não salvei" - que é onde o trabalho se
   * perde quando alguém fecha a aba.
   */
  async function alterarCampo(issue, campo, valor) {
    if (!issue || !issue.chamadoId) return;
    if (issue[campo] === valor) return;

    const anterior = issue[campo];
    issue[campo] = valor;
    render();

    const mudanca = {};
    mudanca[campo] = valor;

    try {
      const atualizado = await PainelApi.alterarChamado(issue.chamadoId, mudanca);
      // `Object.assign` e não substituição: o resto do arquivo guarda ESTA
      // referência desde a última carga, e trocar o objeto faria metade do código
      // continuar olhando para o antigo.
      Object.assign(issue, PainelApi.paraCartao(atualizado));
      render();
      if (openModalKey === issue.key) renderModal(issue);
      showToast(issue.key + ' · ' + (ROTULOS_CAMPO[campo] || campo) + ' atualizado');
    } catch (err) {
      issue[campo] = anterior;
      render();
      if (openModalKey === issue.key) renderModal(issue);
      showToast('Não foi possível alterar ' + (ROTULOS_CAMPO[campo] || campo) +
        ': ' + err.message);
    }
  }

  /* ---------- Montagem do modal ---------------------------------------- */

  function linha(rotulo, conteudo) {
    return '<dt>' + esc(rotulo) + '</dt><dd>' + conteudo + '</dd>';
  }

  function selectHtml(id, opcoes) {
    return '<select class="select" id="' + id + '">' + opcoes + '</select>';
  }

  function textoHtml(id, valor, placeholder, maxlength) {
    return '<input class="field__input" id="' + id + '" type="text" ' +
      'maxlength="' + (maxlength || 200) + '" ' +
      'placeholder="' + esc(placeholder || '') + '" ' +
      'value="' + esc(valor || '') + '">';
  }

  function numeroHtml(id, valor, extra) {
    return '<input class="field__input field__input--num" id="' + id + '" type="number" ' +
      'min="0" ' + (extra || '') + ' value="' + (valor === null || valor === undefined ? '' : valor) +
      '">';
  }

  function caixaHtml(id, marcado, rotulo) {
    return '<label class="conn-toggle"><input type="checkbox" id="' + id + '"' +
      (marcado ? ' checked' : '') + '><span>' + esc(rotulo) + '</span></label>';
  }

  /** Bloco comum: o que vale para os dois tipos de chamado. */
  function blocoClassificacao(issue) {
    const prazo = estadoPrazo(issue);

    return '<div class="settings-label">Classificação</div>' +
      '<dl class="field-grid">' +
        linha('Situação', selectHtml('f-status', optionsFor(columns, issue.status))) +
        // O tipo vem primeiro depois da situação porque é ele que decide qual dos
        // dois blocos abaixo aparece: mudá-lo redesenha o modal.
        linha('Tipo', selectHtml('f-tipo', opcoesLista('tipo', issue.tipo, 'Sem tipo'))) +
        linha('Assunto', selectHtml('f-assunto', '')) +
        linha('Setor responsável', selectHtml('f-setor', '')) +
        linha('Prioridade',
          selectHtml('f-prioridade', opcoesLista('prioridade', issue.prioridade, null))) +
        linha('Responsável', selectHtml('f-responsavel', '')) +
        linha('Canal de origem', selectHtml('f-canal', opcoesLista('canal', issue.canal, null))) +
        linha('Prazo (SLA)',
          '<input class="field__input" id="f-prazo" type="datetime-local" value="' +
          esc(paraDatetimeLocal(issue.prazoEm)) + '">' +
          (prazo ? ' <span class="card__prazo ' + prazo.classe + '">' + esc(prazo.texto) +
            '</span>' : '')) +
        linha('Etiquetas',
          textoHtml('f-tags', (issue.tags || []).join(', '), 'separadas por vírgula', 400)) +
      '</dl>';
  }

  function blocoInterno(issue) {
    return '<div class="settings-label">Chamado interno</div>' +
      '<dl class="field-grid">' +
        linha('Setor de origem', selectHtml('f-setor-origem', '')) +
        linha('Tipo de solicitação',
          selectHtml('f-tipo-solicitacao',
            opcoesLista('tipoSolicitacao', issue.tipoSolicitacao, 'Não classificado'))) +
        linha('Impacto no negócio',
          selectHtml('f-impacto', opcoesLista('impacto', issue.impacto, 'Não avaliado'))) +
        linha('Sistema/processo',
          textoHtml('f-sistema', issue.sistemaAfetado, 'Vetor, fechamento de caixa…', 200)) +
        linha('Tempo estimado',
          numeroHtml('f-tempo-estimado', issue.tempoEstimadoMin, 'step="15"') +
          ' <span class="field-grid__fraco">min · ' +
          esc(minutosLegiveis(issue.tempoEstimadoMin)) + '</span>') +
        linha('Tempo gasto',
          numeroHtml('f-tempo-gasto', issue.tempoGastoMin, 'step="15"') +
          ' <span class="field-grid__fraco">min · ' +
          esc(minutosLegiveis(issue.tempoGastoMin)) + '</span>') +
      '</dl>';
  }

  function blocoFranquia(issue) {
    // O detalhe de custo só aparece com "envolve custo" ligado: valor preenchido
    // com a chave desligada seria ambíguo entre "não envolve dinheiro" e
    // "envolve, mas ninguém estimou".
    const custo = issue.envolveCusto
      ? linha('Valor estimado',
          '<input class="field__input field__input--num" id="f-valor" type="number" ' +
          'min="0" step="0.01" value="' +
          (issue.valorEstimadoCentavos === null ? '' : issue.valorEstimadoCentavos / 100) +
          '"> <span class="field-grid__fraco">' + esc(reais(issue.valorEstimadoCentavos)) +
          '</span>') +
        linha('Aprovação',
          caixaHtml('f-precisa-aprovacao', issue.precisaAprovacao, 'Precisa de aprovação'))
      : '';

    return '<div class="settings-label">Chamado de franquia</div>' +
      '<dl class="field-grid">' +
        linha('Código da unidade', textoHtml('f-franquia-codigo', issue.franquiaCodigo, 'BM-042', 60)) +
        linha('Nome da unidade',
          textoHtml('f-franquia-nome', issue.franquiaNome, 'Loja Shopping Centro', 200)) +
        linha('Franqueado', textoHtml('f-franqueado-nome', issue.franqueadoNome, '', 120)) +
        // O rótulo "Contato" aparece DUAS vezes no detalhe: aqui, o do
        // franqueado, e mais abaixo, o de quem abriu. As seções distinguem, mas
        // quem lê de relance não vê a seção - então o placeholder diz de quem é.
        linha('Contato',
          textoHtml('f-franqueado-contato', issue.franqueadoContato,
            'telefone ou e-mail do franqueado', 200)) +
        linha('Localização', textoHtml('f-localizacao', issue.localizacao, 'Cidade / praça', 200)) +
        linha('Tipo de chamado',
          selectHtml('f-tipo-franquia',
            opcoesLista('tipoFranquia', issue.tipoFranquia, 'Não classificado'))) +
        // Escala própria, separada da prioridade técnica: loja parada é diferente
        // de dúvida sobre material.
        linha('Urgência comercial',
          selectHtml('f-urgencia',
            opcoesLista('urgenciaComercial', issue.urgenciaComercial, 'Não avaliada'))) +
        linha('Cliente final',
          caixaHtml('f-afeta-atendimento', issue.afetaAtendimento,
            'Afeta o atendimento (loja parada, sistema fora do ar)')) +
        linha('Custo',
          caixaHtml('f-envolve-custo', issue.envolveCusto, 'Envolve custo ou reembolso')) +
        custo +
      '</dl>';
  }

  function blocoSolicitante(issue) {
    return '<div class="settings-label">Solicitante</div>' +
      '<dl class="field-grid">' +
        // Nome não é editável: quem abriu pelo WhatsApp escreveu na conversa, e a
        // API não expõe rota para reescrevê-lo. Campo editável que não persiste é
        // pior que campo travado.
        linha('Nome',
          '<span class="field-grid__pessoa">' +
          avatarSolicitante(issue.solicitante, 'avatar--sm') +
          '<span>' + esc(issue.solicitante || '—') + '</span></span>') +
        linha('Contato',
          textoHtml('f-contato', issue.contato,
            'ramal, e-mail ou telefone de quem abriu', 200)) +
        linha('Origem no sistema',
          '<span class="field-grid__fraco">' +
          (issue.origem === 'painel'
            ? 'criado no painel — não há telefone, então não recebe aviso no WhatsApp'
            : 'veio da conversa no WhatsApp') +
          '</span>') +
      '</dl>';
  }

  function blocoSla(issue) {
    const prazo = estadoPrazo(issue);

    return '<div class="settings-label">Prazos</div>' +
      '<dl class="field-grid">' +
        linha('Aberto em', esc(dataLonga(issue.abertoEm)) +
          ' <span class="field-grid__fraco">(' + esc(idadeCurta(issue.abertoEm)) + ')</span>') +
        linha('1º atendimento', marcoSla(issue.abertoEm, issue.primeiroAtendimentoEm)) +
        linha('Concluído', marcoSla(issue.abertoEm, issue.resolvidoEm)) +
        // A condicao e `prazo` e nao `issue.prazoEm`: uma data ilegivel na coluna
        // (linha editada a mao, por exemplo) faz `estadoPrazo` devolver null, e ler
        // `prazo.classe` derrubaria o modal inteiro por causa de um campo.
        linha('Prazo combinado', prazo
          ? esc(dataLonga(issue.prazoEm)) +
            ' <span class="card__prazo ' + prazo.classe + '">' + esc(prazo.texto) + '</span>'
          : '<span class="field-grid__fraco">— sem prazo combinado</span>') +
        linha('Atualizado', esc(dataLonga(issue.atualizadoEm))) +
      '</dl>';
  }

  /**
   * Avaliação pós-fechamento.
   *
   * O formulário só aparece em chamado CONCLUÍDO, porque é o que a rota aceita -
   * mostrar os campos antes disso seria oferecer uma ação que volta 409. Em
   * chamado ainda aberto, a seção explica em vez de desaparecer: some sem
   * explicação é o que faz alguém procurar um campo que existe.
   */
  function blocoAvaliacao(issue) {
    const concluido = issue.status === 'resolvido' || issue.status === 'fechado';

    if (!concluido && issue.avaliacaoNota === null) {
      return '<div class="settings-label">Avaliação</div>' +
        '<p class="modal__nota">A avaliação é pós-fechamento: fica disponível quando o ' +
        'chamado for para <strong>Resolvido</strong> ou <strong>Fechado</strong>.</p>';
    }

    const notas = [1, 2, 3, 4, 5].map((n) =>
      '<option value="' + n + '"' + (issue.avaliacaoNota === n ? ' selected' : '') + '>' +
      n + '</option>'
    ).join('');

    const jaAvaliado = issue.avaliadoEm
      ? '<p class="modal__nota">Avaliado em ' + esc(dataLonga(issue.avaliadoEm)) + '.</p>'
      : '';

    return '<div class="settings-label">Avaliação</div>' +
      '<dl class="field-grid">' +
        linha('Nota',
          '<select class="select" id="f-nota">' +
          '<option value=""' + (issue.avaliacaoNota === null ? ' selected' : '') +
          '>Sem nota</option>' + notas + '</select>') +
        linha('Comentário',
          '<textarea class="field__input" id="f-avaliacao-comentario" rows="2" ' +
          'maxlength="2000" placeholder="o que o solicitante achou">' +
          esc(issue.avaliacaoComentario || '') + '</textarea>') +
        linha('', '<button class="nav-btn" id="f-avaliar">Gravar avaliação</button>') +
      '</dl>' + jaAvaliado;
  }

  /* ---------- Comentários, anexos e dependências ----------------------- */

  /**
   * A conversa do WhatsApp: o que a pessoa escreveu para abrir o chamado.
   *
   * Duas coisas que a tela precisa dizer, e por isso não é só uma lista:
   *
   *   - **de que lado cada mensagem está.** `remetente` é `usuario` ou `sistema`,
   *     e é a única informação de identidade que existe em `Mensagem` — o nome do
   *     solicitante vem do chamado, e do outro lado é o bot.
   *   - **que a conversa TERMINA na abertura do chamado.** Quando a pessoa manda
   *     outra mensagem depois, o bot abre uma sessão nova e aquilo vira outro
   *     chamado. Sem esse aviso, quem atende fica procurando a resposta do cliente
   *     numa lista que, por desenho, não vai crescer.
   *
   * Chamado criado no painel não tem conversa nenhuma (não tem telefone, então não
   * há sessão nem log). Aí a seção explica isso em vez de mostrar lista vazia —
   * vazio sem explicação parece falha de carregamento.
   */
  function conversaHtml(issue) {
    if (issue.origem === 'painel') {
      return '<p class="modal__nota">Este chamado foi criado no painel: não existe ' +
        'conversa de WhatsApp por trás dele, e por isso também não há telefone para ' +
        'avisar o solicitante.</p>';
    }

    if (!detalhe) return '<p class="modal__nota">Carregando…</p>';

    if (detalhe.mensagens.length === 0) {
      return '<p class="modal__nota">Nenhuma mensagem registrada para este chamado.</p>';
    }

    const linhas = detalhe.mensagens.map((m) => {
      const doUsuario = m.remetente === 'usuario';

      // Saída sem `enviadaEm` está na fila da outbox. É a diferença entre "a
      // equipe não respondeu" e "a resposta existe e não saiu daqui", e sem
      // mostrar isso quem atende reenviaria à mão uma mensagem que já vai sair.
      const pendente = !doUsuario && !m.enviadaEm
        ? ' <span class="card__prazo is-perto" title="Ainda na fila de envio">na fila</span>'
        : '';

      const quem = doUsuario
        ? avatarSolicitante(issue.solicitante, 'avatar--sm')
        : '<span class="avatar avatar--sm avatar--bot" title="Mensagem automática do bot">' +
          ICONE_BOT + '</span>';

      const nome = doUsuario ? (issue.solicitante || 'Solicitante') : 'Bot de atendimento';

      return '<li class="thread__item thread__item--' + (doUsuario ? 'entrada' : 'saida') + '">' +
        '<div class="thread__head">' +
          quem +
          '<strong>' + esc(nome) + '</strong>' +
          '<span class="field-grid__fraco">' + esc(dataLonga(m.timestamp)) + '</span>' +
          pendente +
        '</div>' +
        '<div class="thread__texto">' + esc(m.texto) + '</div>' +
      '</li>';
    }).join('');

    return '<ul class="thread thread--conversa">' + linhas + '</ul>' +
      '<p class="modal__nota">Esta é a conversa que abriu o chamado, mais os avisos ' +
      'automáticos de mudança de situação. Ela <strong>não continua</strong>: uma nova ' +
      'mensagem do solicitante começa outra conversa e abre outro chamado. Para falar ' +
      'com ele, use o WhatsApp — o painel ainda não envia mensagem escrita à mão.</p>';
  }

  function comentariosHtml() {
    if (!detalhe) return '<p class="modal__nota">Carregando…</p>';
    if (detalhe.comentarios.length === 0) {
      return '<p class="modal__nota">Nenhum comentário ainda.</p>';
    }

    return '<ul class="thread">' + detalhe.comentarios.map((c) =>
      '<li class="thread__item">' +
        '<div class="thread__head">' +
          avatarSolicitante(c.autor || '?', 'avatar--sm') +
          '<strong>' + esc(c.autor || 'sem autor') + '</strong>' +
          '<span class="field-grid__fraco">' + esc(dataLonga(c.criadoEm)) + '</span>' +
        '</div>' +
        '<div class="thread__texto">' + esc(c.texto) + '</div>' +
      '</li>'
    ).join('') + '</ul>';
  }

  function tamanhoLegivel(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return Math.round(bytes / 1024) + ' KB';
    return (Math.round((bytes / (1024 * 1024)) * 10) / 10) + ' MB';
  }

  function anexosHtml() {
    if (!detalhe) return '<p class="modal__nota">Carregando…</p>';
    if (detalhe.anexos.length === 0) return '<p class="modal__nota">Nenhum anexo.</p>';

    return '<ul class="anexos">' + detalhe.anexos.map((a) =>
      '<li class="anexos__item">' +
        // O download passa pelo fetch (para o token ir no cabeçalho) e não por um
        // href direto - ver `baixarAnexo` em api.js. Por isso é botão, não link.
        '<button class="link-btn" data-anexo="' + a.id + '">' + esc(a.nome) + '</button>' +
        '<span class="field-grid__fraco">' + esc(tamanhoLegivel(a.bytes)) +
        (a.enviadoPor ? ' · ' + esc(a.enviadoPor) : '') + '</span>' +
        '<span class="toolbar__spacer"></span>' +
        '<button class="link-btn modal__delete" data-anexo-excluir="' + a.id +
        '" title="Excluir anexo">Excluir</button>' +
      '</li>'
    ).join('') + '</ul>';
  }

  function ligacoesHtml(lista, vazio) {
    if (lista.length === 0) return '<p class="modal__nota">' + esc(vazio) + '</p>';
    return '<ul class="anexos">' + lista.map((d) =>
      '<li class="anexos__item">' +
        '<span class="card__key">#' + d.chamadoId + '</span>' +
        '<span>' + esc(d.resumo) + '</span>' +
        '<span class="tag">' + esc(nomeColuna(d.situacao)) + '</span>' +
      '</li>'
    ).join('') + '</ul>';
  }

  function dependenciasHtml() {
    if (!detalhe) return '<p class="modal__nota">Carregando…</p>';

    return '<div class="dep">' +
      '<div class="settings-label">Bloqueado por</div>' +
      ligacoesHtml(detalhe.bloqueadoPor, 'Nada está travando este chamado.') +
      detalhe.bloqueadoPor.map((d) =>
        '<button class="link-btn" data-dep-remover="' + d.chamadoId + '">' +
        'Destravar de #' + d.chamadoId + '</button>'
      ).join(' ') +
      '<div class="settings-label">Bloqueia</div>' +
      ligacoesHtml(detalhe.bloqueia, 'Este chamado não trava nenhum outro.') +
    '</div>';
  }

  /**
   * Detalhe do chamado.
   *
   * TUDO o que tem rota para persistir é editável aqui, e a linha continua sendo a
   * mesma de sempre: só entra campo que sabe se gravar. O que mudou é que a
   * classificação passou a ter rota (`PATCH /internal/chamados/:id`), então os 24
   * campos novos entram; resumo, descrição e o nome do solicitante continuam
   * travados, porque foram escritos pela pessoa na conversa do WhatsApp e não há
   * rota para reescrevê-los.
   *
   * Campo editável que não persiste é pior que campo travado: a pessoa digita,
   * fecha, e a mudança evapora em silêncio.
   *
   * Os dois blocos específicos são mutuamente exclusivos e saem do `tipo`. Com
   * `tipo` nulo, nenhum dos dois aparece e no lugar fica o convite a classificar -
   * é o estado em que todo chamado vindo do WhatsApp nasce.
   */
  function modalBodyHtml(issue) {
    let especifico = '';
    if (issue.tipo === 'interno') especifico = blocoInterno(issue);
    else if (issue.tipo === 'franquia') especifico = blocoFranquia(issue);
    else {
      especifico = '<p class="modal__nota">Sem <strong>tipo</strong> definido: escolha ' +
        '<em>Interno</em> ou <em>Franquia</em> acima para o formulário pedir os campos ' +
        'daquele tipo. Chamado que vem do WhatsApp nasce assim — o bot não pergunta ' +
        'isso para não custar mais uma mensagem a todo atendimento.</p>';
    }

    return '<div class="modal__titulo-fixo">' + esc(issue.title) + '</div>' +
      blocoClassificacao(issue) +
      especifico +
      blocoSolicitante(issue) +
      blocoSla(issue) +

      '<div class="settings-label">Descrição</div>' +
      '<dl class="field-grid">' +
        linha('Descrição',
          '<span class="field-grid__texto">' + esc(issue.descricao || '—') + '</span>') +
      '</dl>' +

      blocoAvaliacao(issue) +

      // A conversa vem ANTES dos comentários porque é o que aconteceu primeiro:
      // ela é a entrada do chamado, e a nota interna é a reação da equipe a ela.
      '<div class="settings-label">Conversa no WhatsApp</div>' +
      '<div id="modal-conversa">' + conversaHtml(issue) + '</div>' +

      '<div class="settings-label">Comentários da equipe</div>' +
      '<div id="modal-comentarios">' + comentariosHtml() + '</div>' +
      '<div class="settings-section">' +
        '<textarea class="field__input" id="f-comentario" rows="2" maxlength="4000" ' +
        'placeholder="nota interna — não é enviada ao solicitante"></textarea>' +
        '<button class="nav-btn settings-add" id="f-comentar">Comentar</button>' +
      '</div>' +

      '<div class="settings-label">Anexos</div>' +
      '<div id="modal-anexos">' + anexosHtml() + '</div>' +
      '<div class="settings-section">' +
        '<input type="file" id="f-anexo">' +
        '<p class="modal__nota">Imagem, PDF, texto ou documento do Office.</p>' +
      '</div>' +

      '<div class="settings-label">Dependências</div>' +
      '<div id="modal-dependencias">' + dependenciasHtml() + '</div>' +
      '<div class="settings-section">' +
        '<label class="field"><span class="field__label">Bloqueado pelo chamado nº</span>' +
        '<input class="field__input field__input--num" id="f-dep-numero" type="number" min="1">' +
        '</label>' +
        '<button class="nav-btn settings-add" id="f-dep-add">Marcar dependência</button>' +
      '</div>' +

      '<p class="modal__nota">Cada campo é gravado no banco assim que você sai dele — ' +
      'não há botão de salvar. Resumo, descrição e nome do solicitante vêm da conversa ' +
      'no WhatsApp e não são editáveis. Os marcos de 1º atendimento e conclusão são ' +
      'gravados sozinhos quando o chamado muda de situação.</p>';
  }

  /* ---------- Ligações dos campos do modal ----------------------------- */

  /** Liga um `<select>` a um campo: valor vazio vira `null` (limpar o campo). */
  function ligarSelect(issue, id, campo, converter) {
    const el = byId(id);
    if (!el) return;
    el.addEventListener('change', (ev) => {
      const bruto = ev.target.value;
      alterarCampo(issue, campo, bruto === '' ? null : converter ? converter(bruto) : bruto);
    });
  }

  /**
   * Liga um campo de texto. Grava no `change` (ao sair do campo), não no `input`:
   * um PATCH por tecla digitada seria uma requisição por letra.
   *
   * Texto vazio vira `null` e não `''`: "não informado" tem UMA representação.
   */
  function ligarTexto(issue, id, campo) {
    const el = byId(id);
    if (!el) return;
    el.addEventListener('change', (ev) => {
      const limpo = ev.target.value.trim();
      alterarCampo(issue, campo, limpo === '' ? null : limpo);
    });
  }

  function ligarNumero(issue, id, campo, fator) {
    const el = byId(id);
    if (!el) return;
    el.addEventListener('change', (ev) => {
      const bruto = ev.target.value;
      if (bruto === '') {
        alterarCampo(issue, campo, null);
        return;
      }
      const n = Number(bruto);
      if (!Number.isFinite(n) || n < 0) {
        showToast('Valor inválido em ' + (ROTULOS_CAMPO[campo] || campo));
        renderModal(issue);
        return;
      }
      // `Math.round` no fator: reais viram centavos, e 12.34 * 100 em ponto
      // flutuante dá 1233.9999999999998 - que o servidor recusaria por não ser
      // inteiro.
      alterarCampo(issue, campo, fator ? Math.round(n * fator) : Math.round(n));
    });
  }

  function ligarCaixa(issue, id, campo) {
    const el = byId(id);
    if (!el) return;
    el.addEventListener('change', (ev) => alterarCampo(issue, campo, ev.target.checked));
  }

  /** Quem está logado, para assinar comentário e anexo. */
  function autorAtual() {
    const login = (window.PAINEL_SERVIDOR && window.PAINEL_SERVIDOR.login) || {};
    return login.nome || login.email || '';
  }

  function bindModalFields(issue) {
    byId('f-status').addEventListener('change', (e) => {
      // Vai para o banco. `moverPara` desfaz sozinho se a API recusar.
      moverPara(issue, e.target.value);
    });

    // Assunto tem rota própria (`PATCH .../categoria`) porque veio antes da
    // classificação e não é o mesmo tipo de mudança: ver o comentário de
    // `classificar`.
    const assunto = byId('f-assunto');
    preencherSelectAssunto(assunto, issue.categoriaId, true);
    assunto.addEventListener('change', (e) => {
      classificar(issue, e.target.value === '' ? null : Number(e.target.value));
    });

    // Os três seletores que precisam ser preenchidos com dado carregado (e não
    // com lista fixa de data.js).
    preencherSelectSetor(byId('f-setor'), issue.setorId, true);
    preencherSelectSetor(byId('f-setor-origem'), issue.setorOrigemId, true);
    preencherSelectPessoa(byId('f-responsavel'), issue.responsavelId);

    ligarSelect(issue, 'f-tipo', 'tipo');
    ligarSelect(issue, 'f-setor', 'setorId', Number);
    ligarSelect(issue, 'f-prioridade', 'prioridade');
    ligarSelect(issue, 'f-responsavel', 'responsavelId', Number);
    ligarSelect(issue, 'f-canal', 'canal');
    ligarSelect(issue, 'f-setor-origem', 'setorOrigemId', Number);
    ligarSelect(issue, 'f-tipo-solicitacao', 'tipoSolicitacao');
    ligarSelect(issue, 'f-impacto', 'impacto');
    ligarSelect(issue, 'f-tipo-franquia', 'tipoFranquia');
    ligarSelect(issue, 'f-urgencia', 'urgenciaComercial');

    ligarTexto(issue, 'f-contato', 'contato');
    ligarTexto(issue, 'f-sistema', 'sistemaAfetado');
    ligarTexto(issue, 'f-franquia-codigo', 'franquiaCodigo');
    ligarTexto(issue, 'f-franquia-nome', 'franquiaNome');
    ligarTexto(issue, 'f-franqueado-nome', 'franqueadoNome');
    ligarTexto(issue, 'f-franqueado-contato', 'franqueadoContato');
    ligarTexto(issue, 'f-localizacao', 'localizacao');

    ligarNumero(issue, 'f-tempo-estimado', 'tempoEstimadoMin');
    ligarNumero(issue, 'f-tempo-gasto', 'tempoGastoMin');
    ligarNumero(issue, 'f-valor', 'valorEstimadoCentavos', 100);

    ligarCaixa(issue, 'f-afeta-atendimento', 'afetaAtendimento');
    ligarCaixa(issue, 'f-envolve-custo', 'envolveCusto');
    ligarCaixa(issue, 'f-precisa-aprovacao', 'precisaAprovacao');

    const prazo = byId('f-prazo');
    if (prazo) {
      prazo.addEventListener('change', (e) => {
        alterarCampo(issue, 'prazoEm', deDatetimeLocal(e.target.value));
      });
    }

    ligarTags(issue);
    ligarAvaliacao(issue);
    ligarComentario(issue);
    ligarAnexos(issue);
    ligarDependencias(issue);
  }

  /**
   * Etiquetas: uma caixa de texto separada por vírgula, gravada como conjunto
   * inteiro (`PUT .../tags`).
   *
   * A normalização de verdade (minúsculas, sem repetidas) é do servidor - é o que
   * garante que "PDV" e "pdv" não virem duas etiquetas quando alguém chama a API
   * sem passar por esta tela. Aqui só se separa por vírgula e se tira o vazio.
   */
  function ligarTags(issue) {
    const el = byId('f-tags');
    if (!el) return;

    el.addEventListener('change', async (ev) => {
      const tags = ev.target.value.split(',').map((t) => t.trim()).filter((t) => t !== '');
      const anterior = issue.tags || [];

      try {
        const r = await PainelApi.definirTags(issue.chamadoId, tags);
        issue.tags = r.tags;
        render();
        if (openModalKey === issue.key) renderModal(issue);
        showToast(issue.key + ' · etiquetas atualizadas');
      } catch (err) {
        issue.tags = anterior;
        if (openModalKey === issue.key) renderModal(issue);
        showToast('Não foi possível gravar as etiquetas: ' + err.message);
      }
    });
  }

  function ligarAvaliacao(issue) {
    const botao = byId('f-avaliar');
    if (!botao) return;

    botao.addEventListener('click', async () => {
      const nota = byId('f-nota').value;
      if (nota === '') {
        showToast('Escolha uma nota de 1 a 5');
        return;
      }

      botao.disabled = true;
      try {
        const r = await PainelApi.avaliarChamado(
          issue.chamadoId,
          Number(nota),
          byId('f-avaliacao-comentario').value
        );
        issue.avaliacaoNota = r.avaliacaoNota;
        issue.avaliacaoComentario = r.avaliacaoComentario;
        issue.avaliadoEm = r.avaliadoEm;
        if (openModalKey === issue.key) renderModal(issue);
        showToast(issue.key + ' · avaliação gravada');
      } catch (err) {
        showToast('Não foi possível avaliar: ' + err.message);
      } finally {
        botao.disabled = false;
      }
    });
  }

  function ligarComentario(issue) {
    const botao = byId('f-comentar');
    if (!botao) return;

    botao.addEventListener('click', async () => {
      const campo = byId('f-comentario');
      const texto = campo.value.trim();
      if (texto === '') return;

      botao.disabled = true;
      try {
        const criado = await PainelApi.comentar(issue.chamadoId, texto, autorAtual());
        // Empilha no fim: a lista é uma conversa, e conversa cresce por baixo.
        if (detalhe) detalhe.comentarios.push(criado);
        campo.value = '';
        if (openModalKey === issue.key) renderModal(issue);
      } catch (err) {
        showToast('Não foi possível comentar: ' + err.message);
      } finally {
        botao.disabled = false;
      }
    });
  }

  function ligarAnexos(issue) {
    const entrada = byId('f-anexo');
    if (entrada) {
      entrada.addEventListener('change', async (ev) => {
        const arquivo = ev.target.files && ev.target.files[0];
        if (!arquivo) return;

        entrada.disabled = true;
        try {
          const criado = await PainelApi.enviarAnexo(issue.chamadoId, arquivo, autorAtual());
          if (detalhe) detalhe.anexos.push(criado);
          showToast('Anexo enviado: ' + criado.nome);
          if (openModalKey === issue.key) renderModal(issue);
        } catch (err) {
          showToast('Não foi possível anexar: ' + err.message);
        } finally {
          entrada.disabled = false;
          entrada.value = '';
        }
      });
    }

    const lista = byId('modal-anexos');
    if (!lista) return;

    lista.addEventListener('click', async (ev) => {
      const baixar = ev.target.closest('[data-anexo]');
      if (baixar) {
        await baixarAnexoParaDisco(Number(baixar.dataset.anexo), baixar.textContent);
        return;
      }

      const excluir = ev.target.closest('[data-anexo-excluir]');
      if (!excluir) return;

      const id = Number(excluir.dataset.anexoExcluir);
      if (!window.confirm('Excluir este anexo? Não há como desfazer.')) return;

      try {
        await PainelApi.excluirAnexo(id);
        if (detalhe) detalhe.anexos = detalhe.anexos.filter((a) => a.id !== id);
        if (openModalKey === issue.key) renderModal(issue);
        showToast('Anexo excluído');
      } catch (err) {
        showToast('Não foi possível excluir: ' + err.message);
      }
    });
  }

  /**
   * Baixa o anexo pelo fetch e entrega ao navegador como download.
   *
   * O caminho é indireto porque `<a href>` não carrega cabeçalho: sem o token no
   * servidor, um link direto para `/internal/anexos/:id` levaria 401. Buscando
   * pelo fetch, o `Authorization` vai igual a toda outra chamada, e o Blob vira
   * um download por um link temporário.
   */
  async function baixarAnexoParaDisco(id, nome) {
    try {
      const blob = await PainelApi.baixarAnexo(id);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = nome || 'anexo';
      document.body.appendChild(a);
      a.click();
      a.remove();
      // Sem o revoke, cada download deixaria o arquivo inteiro preso na memória
      // da aba até ela fechar.
      URL.revokeObjectURL(url);
    } catch (err) {
      showToast('Não foi possível baixar: ' + err.message);
    }
  }

  function ligarDependencias(issue) {
    const botao = byId('f-dep-add');
    if (botao) {
      botao.addEventListener('click', async () => {
        const campo = byId('f-dep-numero');
        const numero = Number(campo.value);
        if (!Number.isInteger(numero) || numero < 1) {
          showToast('Informe o número do chamado que está travando este');
          return;
        }

        botao.disabled = true;
        try {
          const criada = await PainelApi.criarDependencia(issue.chamadoId, numero);
          if (detalhe) detalhe.bloqueadoPor.push(criada);
          campo.value = '';
          if (openModalKey === issue.key) renderModal(issue);
          showToast(issue.key + ' está bloqueado por #' + numero);
        } catch (err) {
          showToast('Não foi possível marcar a dependência: ' + err.message);
        } finally {
          botao.disabled = false;
        }
      });
    }

    const lista = byId('modal-dependencias');
    if (!lista) return;

    lista.addEventListener('click', async (ev) => {
      const alvo = ev.target.closest('[data-dep-remover]');
      if (!alvo) return;

      const bloqueadorId = Number(alvo.dataset.depRemover);
      try {
        await PainelApi.removerDependencia(issue.chamadoId, bloqueadorId);
        if (detalhe) {
          detalhe.bloqueadoPor = detalhe.bloqueadoPor.filter(
            (d) => d.chamadoId !== bloqueadorId
          );
        }
        if (openModalKey === issue.key) renderModal(issue);
        showToast('Dependência removida');
      } catch (err) {
        showToast('Não foi possível remover: ' + err.message);
      }
    });
  }

  /**
   * Garante que as cinco listas existam, mesmo que a resposta não as traga.
   *
   * Não é paranoia: o painel é servido como ARQUIVO ESTÁTICO do disco e o bot roda
   * `dist/` compilado, então os dois são atualizados em momentos diferentes. Numa
   * atualização, um `F5` no painel pode cair num bot que ainda não subiu com a
   * rota nova — e aí `detalhe.mensagens` seria `undefined`, o `.length` do render
   * estouraria, e o modal abriria em branco em vez de mostrar os campos, que
   * continuam funcionando.
   *
   * Uma normalização só, aqui, em vez de `|| []` espalhado pelos cinco lugares que
   * leem `detalhe`.
   */
  function normalizarDetalhe(r) {
    return {
      mensagens: r.mensagens || [],
      comentarios: r.comentarios || [],
      anexos: r.anexos || [],
      bloqueadoPor: r.bloqueadoPor || [],
      bloqueia: r.bloqueia || [],
    };
  }

  /**
   * Busca a conversa, os comentários, os anexos e as dependências do chamado
   * aberto.
   *
   * Uma requisição só, e só ao ABRIR: as três listas vêm juntas de
   * `GET /internal/chamados/:id/detalhe`. Falha aqui não fecha o modal - os
   * campos continuam editáveis, e as listas mostram o erro no lugar do conteúdo.
   */
  async function carregarDetalheDoChamado(issue) {
    detalhe = null;
    try {
      const r = await PainelApi.carregarDetalhe(issue.chamadoId);
      // O modal pode ter fechado, ou trocado de chamado, enquanto isto voltava.
      if (openModalKey !== issue.key) return;
      detalhe = normalizarDetalhe(r);
      renderModal(issue);
    } catch (err) {
      if (openModalKey !== issue.key) return;
      // A forma vazia precisa ter TODAS as listas: `conversaHtml` e as outras
      // leem direto de `detalhe`, e uma chave faltando aqui viraria TypeError no
      // meio do caminho de erro — o pior lugar para um segundo erro.
      detalhe = { mensagens: [], comentarios: [], anexos: [], bloqueadoPor: [], bloqueia: [] };
      renderModal(issue);
      showToast('Não foi possível carregar comentários e anexos: ' + err.message);
    }
  }

  function renderModal(issue) {
    byId('modal-key').innerHTML = ICONS.task + ' ' + esc(issue.key);
    byId('modal-body').innerHTML = modalBodyHtml(issue);
    bindModalFields(issue);
  }

  function openModal(key) {
    const issue = findIssue(key);
    if (!issue) return;
    openModalKey = key;

    // `detalhe` do chamado ANTERIOR não pode sobrar na tela: sem esta linha, o
    // modal abriria mostrando os comentários do cartão que estava aberto antes,
    // até a busca voltar.
    detalhe = null;

    renderModal(issue);
    byId('modal').classList.add('is-open');
    byId('modal').setAttribute('aria-hidden', 'false');
    byId('modal-backdrop').classList.add('is-open');
    // O título é texto fixo; o foco vai para o primeiro campo editável.
    byId('f-status').focus();

    // Comentários, anexos e dependências vêm depois, numa requisição só. O modal
    // já está utilizável antes disso: os campos de classificação saem do cartão,
    // que já está carregado.
    carregarDetalheDoChamado(issue);
  }

  function closeModal() {
    openModalKey = null;
    // Solta as listas: elas valem para UM chamado, e guardá-las faria o próximo
    // modal abrir com o conteúdo do anterior.
    detalhe = null;
    byId('modal').classList.remove('is-open');
    byId('modal').setAttribute('aria-hidden', 'true');
    byId('modal-backdrop').classList.remove('is-open');
  }

  function setupModal() {
    byId('modal-backdrop').addEventListener('click', closeModal);
    byId('modal-close').addEventListener('click', closeModal);

    // Sinalizar e excluir ficaram sem função: as duas mexiam em estado local, e
    // agora o cartão é uma linha do banco. Excluir, em especial, sumiria com
    // o chamado do quadro sem apagar nada no banco - o pior tipo de botão.
    // Apagar chamado é obrigação de LGPD e tem caminho próprio, auditável:
    // `npm run retencao -- --esquecer <telefone> --confirmar`.
    byId('modal-flag').setAttribute('hidden', '');
    byId('modal-delete').setAttribute('hidden', '');

    byId('modal-done').addEventListener('click', closeModal);

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && openModalKey) closeModal();
    });
  }

  /* ---------- Arrastar e soltar --------------------------------------- */

  let draggingKey = null;

  function setupDragAndDrop() {
    const board = byId('board');

    board.addEventListener('dragstart', (e) => {
      const card = e.target.closest('.card');
      if (!card) return;
      draggingKey = card.dataset.key;
      card.classList.add('is-dragging');
      e.dataTransfer.effectAllowed = 'move';
      e.dataTransfer.setData('text/plain', draggingKey);
    });

    board.addEventListener('dragend', () => {
      draggingKey = null;
      board.querySelectorAll('.is-over').forEach((el) => el.classList.remove('is-over'));
      render();
    });

    board.addEventListener('dragover', (e) => {
      const zone = e.target.closest('[data-drop]');
      if (!zone || !draggingKey) return;
      e.preventDefault();
      e.dataTransfer.dropEffect = 'move';
      zone.closest('.column').classList.add('is-over');
    });

    board.addEventListener('dragleave', (e) => {
      const zone = e.target.closest('[data-drop]');
      if (zone && !zone.contains(e.relatedTarget)) {
        zone.closest('.column').classList.remove('is-over');
      }
    });

    board.addEventListener('drop', (e) => {
      const zone = e.target.closest('[data-drop]');
      if (!zone || !draggingKey) return;
      e.preventDefault();
      const issue = findIssue(draggingKey);
      draggingKey = null;
      if (issue) moverPara(issue, zone.dataset.drop);
    });

    board.addEventListener('click', (e) => {
      const card = e.target.closest('.card');
      if (card) openModal(card.dataset.key);
    });

    board.addEventListener('keydown', (e) => {
      const card = e.target.closest('.card');
      if (card && (e.key === 'Enter' || e.key === ' ')) {
        e.preventDefault();
        openModal(card.dataset.key);
      }
    });
  }

  /* ---------- Conexão com a API --------------------------------------- */

  let carregando = false;
  let ultimoErro = null;
  let ultimaAtualizacao = null;
  let timerAtualizacao = null;

  function estadoConexao() {
    if (!PainelApi.temToken()) return { classe: 'is-off', texto: 'sem token' };
    if (carregando) return { classe: 'is-loading', texto: 'atualizando…' };
    if (ultimoErro) return { classe: 'is-error', texto: ultimoErro };
    if (ultimaAtualizacao) {
      return {
        classe: 'is-ok',
        texto: 'sincronizado às ' +
          ultimaAtualizacao.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' }),
      };
    }
    return { classe: '', texto: '—' };
  }

  function renderConexao() {
    const estado = estadoConexao();
    const chip = byId('conn-status');
    if (chip) {
      chip.textContent = estado.texto;
      // `renderConexao` reescreve a className inteira a cada render, então a
      // classe inerte precisa entrar aqui - posta uma vez no setup, sumiria.
      chip.className = 'sprint-chip conn-status ' + estado.classe +
        (PainelApi.tokenNoServidor() ? ' conn-status--inerte' : '');
    }
    const btn = byId('conn-refresh');
    if (btn) btn.disabled = carregando;

    const aviso = byId('conn-avisar');
    if (aviso) aviso.checked = PainelApi.avisarUsuario();
  }

  /**
   * Recarrega os chamados do banco, substituindo o que está na tela.
   *
   * `issues` é mutado no lugar (length = 0 + push) porque o resto do arquivo
   * guarda essa mesma referência desde o boot; trocar por um array novo faria
   * metade do código continuar olhando para o antigo.
   */
  async function carregarChamados(opcoes) {
    const silencioso = !!(opcoes && opcoes.silencioso);

    if (!PainelApi.temToken()) {
      ultimoErro = null;
      renderConexao();
      return;
    }

    carregando = true;
    renderConexao();

    try {
      const resposta = await PainelApi.listarChamados();
      issues.length = 0;
      resposta.chamados.forEach((c) => issues.push(PainelApi.paraCartao(c)));
      ultimoErro = null;
      ultimaAtualizacao = new Date();
      render();

      // O modal aberto está apontando para um objeto que acabou de ser
      // descartado: reabre no cartão equivalente para não editar um fantasma.
      if (openModalKey) {
        const atual = findIssue(openModalKey);
        if (atual) renderModal(atual);
        else closeModal();
      }
    } catch (err) {
      ultimoErro = err.message;
      if (!silencioso) showToast('Não foi possível carregar: ' + err.message);
    } finally {
      carregando = false;
      renderConexao();
    }
  }

  /**
   * Move um chamado e persiste no banco.
   *
   * Atualiza a tela primeiro e desfaz se a API recusar: numa fila de suporte o
   * arrastar precisa responder na hora, e a falha é o caso raro.
   */
  async function moverPara(issue, novaSituacao) {
    if (!issue || !issue.chamadoId) return;
    if (issue.status === novaSituacao) return;

    const anterior = issue.status;
    issue.status = novaSituacao;
    render();

    try {
      // Tarefa não tem telefone: pedir aviso seria aceito pelo servidor e não
      // enviaria nada (ele registra um warn e devolve `notificado: false`). Em vez
      // de mandar um pedido que nunca vale, o quadro não o faz - a preferência
      // "avisar" continua valendo para chamado de conversa.
      const avisar = issue.origem === 'painel' ? false : PainelApi.avisarUsuario();
      const r = await PainelApi.moverChamado(issue.chamadoId, novaSituacao, avisar);
      issue.status = r.situacao;
      issue.atualizadoEm = new Date().toISOString();
      // Os marcos vêm na resposta do PATCH justamente para isto: o detalhe mostra
      // "1º atendimento" na hora, sem esperar a próxima listagem. Quem decide os
      // valores é o servidor - copiar a regra aqui seria a segunda cópia, que é
      // a que erra.
      issue.primeiroAtendimentoEm = r.primeiroAtendimentoEm || null;
      issue.resolvidoEm = r.resolvidoEm || null;
      render();
      if (openModalKey === issue.key) renderModal(issue);

      showToast(
        issue.key + ' → ' + nomeColuna(r.situacao) +
        (r.notificado ? ' · usuário avisado no WhatsApp' : '')
      );
    } catch (err) {
      issue.status = anterior;
      render();
      if (openModalKey === issue.key) renderModal(issue);
      showToast('Não foi possível mover ' + issue.key + ': ' + err.message);
    }
  }

  /**
   * Troca o assunto do chamado e persiste.
   *
   * Mesmo desenho de `moverPara` - tela primeiro, desfaz se a API recusar -, mas
   * por uma rota separada: classificar não é evento de atendimento. Não avisa o
   * usuário, não entra na auditoria de situação e não move marco de SLA.
   */
  async function classificar(issue, categoriaId) {
    if (!issue || !issue.chamadoId) return;
    if (issue.categoriaId === categoriaId) return;

    const anterior = issue.categoriaId;
    issue.categoriaId = categoriaId;
    render();

    try {
      await PainelApi.definirAssunto(issue.chamadoId, categoriaId);
      showToast(
        issue.key + ' → ' + (categoriaId ? caminhoAssunto(categoriaId) : 'sem assunto')
      );
    } catch (err) {
      issue.categoriaId = anterior;
      render();
      if (openModalKey === issue.key) renderModal(issue);
      showToast('Não foi possível classificar ' + issue.key + ': ' + err.message);
    }
  }

  function agendarAtualizacao() {
    if (timerAtualizacao) clearInterval(timerAtualizacao);
    const seg = (window.PAINEL_CONFIG && window.PAINEL_CONFIG.atualizarASegundos) || 0;
    if (seg <= 0) return;
    // Silencioso: uma falha de rede no fundo não deve encher a tela de avisos.
    // O chip de estado já mostra que algo está errado.
    timerAtualizacao = setInterval(() => carregarChamados({ silencioso: true }), seg * 1000);
  }

  function setupConexao() {
    // O "Atualizar" recarrega a árvore de assuntos junto: se outro atendente
    // acrescentou um assunto, é por aqui que ele aparece sem recarregar a página.
    // A atualização automática NÃO faz isso - assunto muda raramente, e não vale
    // uma requisição a cada 30 segundos.
    byId('conn-refresh').addEventListener('click', async () => {
      // A configuração entra na mesma leva: ela agora é compartilhada, então
      // "Atualizar" é o momento em que a renomeação feita por outro atendente
      // aparece aqui, junto com os assuntos e setores que ele criou.
      await carregarConfiguracao();
      await carregarAssuntos();
      await carregarSetores();
      await carregarPessoas();
      await carregarChamados();
    });

    byId('conn-avisar').addEventListener('change', (e) => {
      PainelApi.definirAvisarUsuario(e.target.checked);
      showToast(
        e.target.checked
          ? 'Mover um chamado vai avisar o usuário no WhatsApp'
          : 'Mover um chamado NÃO vai mais avisar o usuário'
      );
    });

    byId('token-form').addEventListener('submit', async (e) => {
      e.preventDefault();
      const campo = byId('token-input');
      PainelApi.gravarToken(campo.value.trim(), byId('token-lembrar').checked);
      campo.value = '';
      fecharToken();
      // Assuntos primeiro: sem a árvore em memória, os cartões renderizariam sem
      // rótulo até a próxima atualização.
      await carregarAssuntos();
      await carregarChamados();
    });

    byId('token-sair').addEventListener('click', () => {
      PainelApi.gravarToken('', false);
      issues.length = 0;
      assuntos = [];
      assuntosPorId = {};
      renderFiltroAssunto();
      ultimaAtualizacao = null;
      ultimoErro = null;
      render();
      renderConexao();
      abrirToken();
    });

    // Com o token no servidor não há token para trocar: o chip deixa de abrir
    // o modal, que só ofereceria um campo sem efeito nenhum.
    if (!PainelApi.tokenNoServidor()) {
      byId('conn-status').addEventListener('click', abrirToken);
    }
  }

  function abrirToken() {
    byId('token-lembrar').checked = PainelApi.lembrando();
    byId('token-modal').classList.add('is-open');
    byId('token-modal').setAttribute('aria-hidden', 'false');
    byId('token-backdrop').classList.add('is-open');
    byId('token-input').focus();
  }

  function fecharToken() {
    byId('token-modal').classList.remove('is-open');
    byId('token-modal').setAttribute('aria-hidden', 'true');
    byId('token-backdrop').classList.remove('is-open');
  }

  /* ---------- Barra de filtros ---------------------------------------- */

  function bindSearch(inputId, mirrorId) {
    byId(inputId).addEventListener('input', (e) => {
      filters.text = e.target.value.trim().toLowerCase();
      const mirror = byId(mirrorId);
      if (mirror && mirror.value !== e.target.value) mirror.value = e.target.value;
      render();
    });
  }

  function setupToolbar() {
    bindSearch('filter-text', 'global-search');

    byId('filter-categoria').addEventListener('change', (e) => {
      filters.categoria = e.target.value;
      render();
    });

    // Os três filtros novos, todos com o mesmo desenho: guarda a escolha e
    // repinta. Quem decide o que cada valor significa é `passaFiltro`.
    byId('filter-setor').addEventListener('change', (e) => {
      filters.setor = e.target.value;
      render();
    });

    const selTipo = byId('filter-tipo');
    selTipo.innerHTML = '<option value="all">Tipo</option>' +
      '<option value="none">Sem tipo</option>' + opcoesLista('tipo', null, null);
    selTipo.addEventListener('change', (e) => {
      filters.tipo = e.target.value;
      render();
    });

    const selPrioridade = byId('filter-prioridade');
    selPrioridade.innerHTML = '<option value="all">Prioridade</option>' +
      opcoesLista('prioridade', null, null);
    selPrioridade.addEventListener('change', (e) => {
      filters.prioridade = e.target.value;
      render();
    });

    byId('filter-type').addEventListener('change', (e) => {
      filters.type = e.target.value;
      render();
    });


    const group = byId('avatar-group');
    renderAvatarGroup();

    group.addEventListener('click', (e) => {
      const btn = e.target.closest('[data-person]');
      if (!btn) return;
      const id = btn.dataset.person;
      filters.assignee = filters.assignee === id ? null : id;
      syncAvatarGroup(group);
      render();
    });

    byId('clear-filters').addEventListener('click', () => {
      filters = { ...EMPTY_FILTERS };
      byId('filter-text').value = '';
      const globalSearch = byId('global-search');
      if (globalSearch) globalSearch.value = '';
      byId('filter-categoria').value = 'all';
      byId('filter-setor').value = 'all';
      byId('filter-tipo').value = 'all';
      byId('filter-prioridade').value = 'all';
      byId('filter-type').value = 'all';
      syncAvatarGroup(group);
      render();
    });
  }

  /**
   * As bolhas de perfil, que filtram por RESPONSÁVEL.
   *
   * Voltaram a ter função com a classificação: antes ficavam ocultas porque
   * chamado não tinha responsável, e um filtro sobre coluna inexistente não
   * filtra nada. Agora `Chamado.responsavelId` existe.
   */
  function renderAvatarGroup() {
    const group = byId('avatar-group');
    group.innerHTML = people.map((p) =>
      `<button class="avatar" data-person="${p.id}" style="background:${esc(p.color)}" ` +
      `title="${esc(p.name)}" aria-label="Filtrar por ${esc(p.name)}">${esc(initials(p.name))}</button>`
    ).join('');
    syncAvatarGroup(group);
  }

  function syncAvatarGroup(group) {
    [...group.children].forEach((el) => {
      el.classList.toggle('is-active', el.dataset.person === filters.assignee);
    });
  }

  /* ---------- Notificações (toasts) ----------------------------------- */

  function showToast(message) {
    const host = byId('toasts');
    if (!host) return;

    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.textContent = message;
    host.appendChild(toast);

    setTimeout(() => {
      toast.classList.add('is-leaving');
      toast.addEventListener('transitionend', () => toast.remove(), { once: true });
    }, 2600);
  }

  /* ---------- Ações do cabeçalho e da navegação ----------------------- */

  /**
   * CHAMADO não nasce no quadro - ele nasce da conversa no WhatsApp. TAREFA
   * nasce aqui: é o mesmo cartão, na mesma coluna, sem conversa por trás e sem
   * telefone (POST /internal/tarefas fixa `origem: 'painel'`).
   *
   * Até 2026-08-27 este botão só explicava que não dava para criar nada. A
   * distinção que ele fazia continua verdadeira para chamado; o que mudou é que
   * existe uma segunda coisa que o quadro PODE criar.
   */
  function createIssue() {
    abrirTarefa();
  }

  /* ---------- Nova tarefa --------------------------------------------- */

  let tarefaAberta = false;

  /**
   * Os campos do formulário, com o tipo de cada um.
   *
   * Uma tabela em vez de vinte linhas de `byId(...).value`: os três laços que
   * usam esta lista - preencher, limpar e ler - percorrem a MESMA definição, e é
   * o que garante que um campo acrescentado aqui apareça nos três. Antes, um
   * campo novo esquecido no "limpar" reapareceria preenchido no chamado seguinte.
   *
   * `bloco` diz a qual dos dois formulários o campo pertence: 'interno',
   * 'franquia' ou vazio (tronco comum). É o que `lerCampos` usa para NÃO mandar
   * dado do bloco escondido - digitar em franquia, trocar para interno e criar
   * não pode levar o código da unidade junto.
   */
  const CAMPOS_TAREFA = [
    { el: 'tarefa-tipo', campo: 'tipo', kind: 'lista', lista: 'tipo', vazio: 'Escolha o tipo' },
    { el: 'tarefa-canal', campo: 'canal', kind: 'lista', lista: 'canal' },
    { el: 'tarefa-setor', campo: 'setorId', kind: 'setor' },
    { el: 'tarefa-prioridade', campo: 'prioridade', kind: 'lista', lista: 'prioridade' },
    { el: 'tarefa-responsavel', campo: 'responsavelId', kind: 'pessoa' },
    { el: 'tarefa-prazo', campo: 'prazoEm', kind: 'datahora' },
    { el: 'tarefa-contato', campo: 'contato', kind: 'texto' },

    { el: 'tarefa-setor-origem', campo: 'setorOrigemId', kind: 'setor', bloco: 'interno' },
    { el: 'tarefa-tipo-solicitacao', campo: 'tipoSolicitacao', kind: 'lista',
      lista: 'tipoSolicitacao', vazio: 'Não classificado', bloco: 'interno' },
    { el: 'tarefa-impacto', campo: 'impacto', kind: 'lista', lista: 'impacto',
      vazio: 'Não avaliado', bloco: 'interno' },
    { el: 'tarefa-sistema', campo: 'sistemaAfetado', kind: 'texto', bloco: 'interno' },
    { el: 'tarefa-tempo-estimado', campo: 'tempoEstimadoMin', kind: 'numero', bloco: 'interno' },

    { el: 'tarefa-franquia-codigo', campo: 'franquiaCodigo', kind: 'texto', bloco: 'franquia' },
    { el: 'tarefa-franquia-nome', campo: 'franquiaNome', kind: 'texto', bloco: 'franquia' },
    { el: 'tarefa-franqueado-nome', campo: 'franqueadoNome', kind: 'texto', bloco: 'franquia' },
    { el: 'tarefa-franqueado-contato', campo: 'franqueadoContato', kind: 'texto',
      bloco: 'franquia' },
    { el: 'tarefa-localizacao', campo: 'localizacao', kind: 'texto', bloco: 'franquia' },
    { el: 'tarefa-tipo-franquia', campo: 'tipoFranquia', kind: 'lista', lista: 'tipoFranquia',
      vazio: 'Não classificado', bloco: 'franquia' },
    { el: 'tarefa-urgencia', campo: 'urgenciaComercial', kind: 'lista',
      lista: 'urgenciaComercial', vazio: 'Não avaliada', bloco: 'franquia' },
    { el: 'tarefa-afeta-atendimento', campo: 'afetaAtendimento', kind: 'caixa',
      bloco: 'franquia' },
    { el: 'tarefa-envolve-custo', campo: 'envolveCusto', kind: 'caixa', bloco: 'franquia' },
    { el: 'tarefa-valor', campo: 'valorEstimadoCentavos', kind: 'reais', bloco: 'franquia' },
    { el: 'tarefa-precisa-aprovacao', campo: 'precisaAprovacao', kind: 'caixa',
      bloco: 'franquia' },
  ];

  /**
   * Mostra o bloco do tipo escolhido e esconde o outro.
   *
   * Sem tipo, nenhum dos dois aparece: é o estado inicial do formulário, e mostrar
   * os dois somaria 17 campos numa tela em que no máximo 11 fazem sentido.
   */
  function sincronizarBlocosTarefa() {
    const tipo = byId('tarefa-tipo').value;
    document.querySelectorAll('#tarefa-modal [data-bloco]').forEach((el) => {
      el.hidden = el.dataset.bloco !== tipo;
    });

    // O detalhe de custo depende da caixa, não do tipo - e ele vive dentro do
    // bloco de franquia, então só importa quando aquele está visível.
    byId('tarefa-custo-detalhe').hidden = !byId('tarefa-envolve-custo').checked;
  }

  function preencherFormularioTarefa() {
    CAMPOS_TAREFA.forEach((c) => {
      const el = byId(c.el);
      if (!el) return;

      if (c.kind === 'lista') {
        preencherSelectLista(el, c.lista, null, c.vazio || null);
      } else if (c.kind === 'setor') {
        // Só os ativos: um chamado novo não tem por que nascer num setor que saiu
        // de circulação.
        preencherSelectSetor(el, null, true);
      } else if (c.kind === 'pessoa') {
        preencherSelectPessoa(el, null);
      } else if (c.kind === 'caixa') {
        el.checked = false;
      } else {
        el.value = '';
      }
    });

    // O assunto tem função própria por causa da árvore (recuo e caminho).
    preencherSelectAssunto(byId('tarefa-categoria'), null, true);

    byId('tarefa-resumo').value = '';
    byId('tarefa-nome').value = '';
    byId('tarefa-descricao').value = '';
    byId('tarefa-tags').value = '';

    // `prioridade` e `canal` são NOT NULL no banco e o `<select>` deles não tem
    // opção vazia: começam no valor que o servidor usaria de qualquer forma.
    byId('tarefa-prioridade').value = 'media';
    // `presencial` e não `whatsapp`: este chamado está sendo DIGITADO por alguém,
    // então não chegou pelo bot. É o mesmo padrão que a rota aplica.
    byId('tarefa-canal').value = 'presencial';

    sincronizarBlocosTarefa();
  }

  function abrirTarefa() {
    if (!PainelApi.temToken()) {
      showToast('Informe o token do painel antes de criar chamado');
      return;
    }
    tarefaAberta = true;
    byId('tarefa-erro').hidden = true;
    preencherFormularioTarefa();
    byId('tarefa-modal').classList.add('is-open');
    byId('tarefa-modal').setAttribute('aria-hidden', 'false');
    byId('tarefa-backdrop').classList.add('is-open');
    byId('tarefa-tipo').focus();
  }

  function fecharTarefa() {
    tarefaAberta = false;
    byId('tarefa-modal').classList.remove('is-open');
    byId('tarefa-modal').setAttribute('aria-hidden', 'true');
    byId('tarefa-backdrop').classList.remove('is-open');
  }

  /**
   * Lê o formulário e devolve o corpo do POST.
   *
   * Duas regras que valem para todos os campos:
   *
   *   - campo do bloco ESCONDIDO não entra. Quem preencheu franquia e depois
   *     trocou para interno não quer o código da unidade no chamado, e mandá-lo
   *     gravaria dado que a tela nem mostra mais.
   *   - campo vazio é OMITIDO em vez de mandado como `null`. Na criação as duas
   *     coisas dão no mesmo (a coluna nasce nula), e omitir mantém o corpo do
   *     tamanho do que a pessoa realmente preencheu.
   */
  function lerCamposTarefa() {
    const tipoEscolhido = byId('tarefa-tipo').value;
    const corpo = {};

    CAMPOS_TAREFA.forEach((c) => {
      if (c.bloco && c.bloco !== tipoEscolhido) return;

      const el = byId(c.el);
      if (!el) return;

      if (c.kind === 'caixa') {
        // Booleano vai sempre, mesmo `false`: a coluna é NOT NULL, e "não afeta o
        // atendimento" é uma resposta, não a ausência de uma.
        corpo[c.campo] = el.checked;
        return;
      }

      const bruto = String(el.value).trim();
      if (bruto === '') return;

      if (c.kind === 'numero') {
        const n = Number(bruto);
        if (Number.isFinite(n) && n >= 0) corpo[c.campo] = Math.round(n);
      } else if (c.kind === 'reais') {
        const n = Number(bruto);
        // `Math.round` porque 12.34 * 100 em ponto flutuante dá
        // 1233.9999999999998, e o servidor recusa o que não é inteiro.
        if (Number.isFinite(n) && n >= 0) corpo[c.campo] = Math.round(n * 100);
      } else if (c.kind === 'datahora') {
        const iso = deDatetimeLocal(bruto);
        if (iso) corpo[c.campo] = iso;
      } else if (c.kind === 'setor' || c.kind === 'pessoa') {
        corpo[c.campo] = Number(bruto);
      } else {
        corpo[c.campo] = bruto;
      }
    });

    return corpo;
  }

  async function salvarTarefa() {
    const botao = byId('tarefa-salvar');
    const erro = byId('tarefa-erro');
    const resumo = byId('tarefa-resumo').value.trim();
    const nome = byId('tarefa-nome').value.trim();
    const descricao = byId('tarefa-descricao').value.trim();
    const categoria = byId('tarefa-categoria').value;

    // Mesmo mínimo do servidor (MIN_CARACTERES). Conferir aqui é conforto, não
    // garantia: quem manda é o POST, que revalida depois do trim.
    if (resumo.length < 2 || nome.length < 2 || descricao.length < 2) {
      erro.textContent = 'Título, solicitante e descrição precisam de ao menos 2 caracteres.';
      erro.hidden = false;
      return;
    }

    const corpo = lerCamposTarefa();
    corpo.nome = nome;
    corpo.resumo = resumo;
    corpo.descricao = descricao;
    corpo.categoriaId = categoria === '' ? null : Number(categoria);

    // Etiquetas vão no MESMO POST: a rota as resolve com `connectOrCreate`, então
    // não é preciso um segundo pedido para elas.
    const tags = byId('tarefa-tags').value.split(',')
      .map((t) => t.trim()).filter((t) => t !== '');
    if (tags.length) corpo.tags = tags;

    // Trava o botão: dois cliques criariam dois chamados iguais, e não existe
    // chave que os impeça no banco (ao contrário do wamid das mensagens).
    botao.disabled = true;
    erro.hidden = true;
    try {
      await PainelApi.criarTarefa(corpo);
      fecharTarefa();
      showToast('Chamado criado');
      // Recarrega em vez de inserir o cartão à mão: a listagem é a única forma
      // de um cartão chegar à tela, então não há dois caminhos para divergir.
      await carregarChamados({ silencioso: true });
    } catch (e) {
      erro.textContent = 'Não foi possível criar: ' + (e && e.message ? e.message : 'erro');
      erro.hidden = false;
    } finally {
      botao.disabled = false;
    }
  }

  function setupTarefa() {
    byId('tarefa-backdrop').addEventListener('click', fecharTarefa);
    byId('tarefa-close').addEventListener('click', fecharTarefa);
    byId('tarefa-salvar').addEventListener('click', salvarTarefa);
    // Os dois campos que mudam a FORMA do formulário, e não só um valor.
    byId('tarefa-tipo').addEventListener('change', sincronizarBlocosTarefa);
    byId('tarefa-envolve-custo').addEventListener('change', sincronizarBlocosTarefa);
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && tarefaAberta) fecharTarefa();
    });
  }

  /* ---------- Resumo (métricas) ---------------------------------------- */

  /**
   * O botão "Resumo" já não conta os cartões da tela.
   *
   * Contar aqui só sabia do que estava carregado e filtrado - dois vieses que
   * ninguém enxerga olhando o número. Os valores agora vêm de /internal/metricas,
   * agregados no banco, com janela própria: é a mesma pergunta ("como está o
   * atendimento") respondida sobre o histórico inteiro em vez de sobre a tela.
   *
   * Arquivar continua não existindo: tirar cartão resolvido da tela não muda
   * nada no banco, e eles voltariam na atualização seguinte. O histórico sai de
   * lá pelo prazo de retenção (`npm run retencao`), não por um botão de quadro.
   */
  function kpiHtml(valor, rotulo) {
    return '<div class="kpi"><div class="kpi__valor">' + esc(valor) + '</div>' +
      '<div class="kpi__rotulo">' + esc(rotulo) + '</div></div>';
  }

  // O tamanho da amostra viaja junto com a média. Sem ele, "12 min" calculado
  // sobre um chamado é lido igual a "12 min" sobre duzentos.
  function amostraHtml(n) {
    return n > 0 ? ' <span class="metricas-amostra">(' + n + ')</span>' : '';
  }

  /**
   * Uma tabela de grupos: assunto, setor ou tipo.
   *
   * Escrita uma vez e usada três porque as três respostas têm a MESMA forma - o
   * servidor devolve `porCategoria`, `porSetor` e `porTipo` com o mesmo schema de
   * linha, justamente para isto. Triplicar o HTML triplicaria a chance de uma das
   * tabelas esquecer uma coluna de situação.
   */
  function tabelaMetricas(titulo, cabecaGrupo, linhas) {
    if (!linhas || linhas.length === 0) return '';

    const corpo = linhas.map((c) =>
      '<tr>' +
        '<td>' + esc(c.rotulo) + '</td>' +
        '<td>' + c.total + '</td>' +
        '<td>' + c.aberto + '</td>' +
        '<td>' + c.em_andamento + '</td>' +
        '<td>' + c.aguardando_resposta + '</td>' +
        '<td>' + c.resolvido + '</td>' +
        '<td>' + c.fechado + '</td>' +
        '<td>' + c.cancelado + '</td>' +
        '<td>' + esc(duracaoMin(c.atendimentoMedioMin)) + amostraHtml(c.atendidos) + '</td>' +
        '<td>' + esc(duracaoMin(c.resolucaoMediaMin)) + amostraHtml(c.resolvidos) + '</td>' +
      '</tr>'
    ).join('');

    return '<div class="settings-label">' + esc(titulo) + '</div>' +
      '<div class="metricas-rolagem"><table class="metricas-tabela">' +
        '<thead><tr>' +
          '<th>' + esc(cabecaGrupo) + '</th><th>Total</th><th>A fazer</th><th>Andamento</th>' +
          '<th>Aguardando</th><th>Resolvidos</th><th>Fechados</th><th>Cancelados</th>' +
          '<th>1º atend.</th><th>Resolução</th>' +
        '</tr></thead>' +
        '<tbody>' + corpo + '</tbody>' +
      '</table></div>';
  }

  /* ==================== Placas e gráficos do dashboard ==================
     A referência do pedido é um painel de Grafana: fileira de placas de cor
     cheia no topo, seções recolhíveis com gráficos de área/linha abaixo.

     A diferença de fundo entre aquele painel e este banco decide o que é
     possível aqui: lá toda métrica é uma TAXA AMOSTRADA (um agente grava
     "mensagens por segundo" a cada 15s); aqui existem EVENTOS com data. Taxa
     sai direto - é contar evento por balde. Quantidade acumulada (o tamanho da
     fila às 18h de terça) não está gravada em lugar nenhum e é RECONSTRUÍDA
     pelo servidor a partir de `MudancaSituacao` - ver o cabeçalho de
     `src/internal/series.ts`.

     Nada de biblioteca de gráfico: o SVG é montado aqui, como todo o resto
     deste painel. */

  /**
   * Os dados de cada gráfico já desenhado, para a camada de leitura.
   *
   * Ficam num mapa em memória e não num `data-` no HTML: são até 90 baldes com
   * uma dúzia de números cada, e enfiar isso num atributo por gráfico
   * multiplicaria o tamanho da página por nada.
   */
  const graficos = new Map();
  let proximoGrafico = 0;

  const LARGURA_SVG = 1000;

  /** Formata o valor de uma série conforme o que ela mede. */
  function valorSerie(v, formato) {
    if (v === null || v === undefined) return '—';
    return formato === 'duracao' ? duracaoMin(v) : String(v);
  }

  /** Rótulo do balde, na resolução em que ele está. */
  function rotuloBalde(iso, balde) {
    const d = new Date(iso);
    if (balde === 'hora') {
      return d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
    }
    const curto = d.toLocaleDateString('pt-BR', { day: '2-digit', month: 'short' });
    return balde === 'semana' ? 'sem. de ' + curto : curto;
  }

  /**
   * Monta o SVG de um gráfico de área/linha.
   *
   * `preserveAspectRatio="none"` estica o desenho na largura para preencher o
   * cartão - é o que deixa o gráfico responsivo sem recalcular nada em JS. O
   * preço é que traço e texto sairiam deformados na horizontal: os traços se
   * salvam com `vector-effect="non-scaling-stroke"` (a espessura passa a ser em
   * pixels de tela, não do viewBox) e o texto não entra no SVG - os rótulos dos
   * eixos são HTML, ao lado.
   */
  function svgSerie(spec, baldes) {
    const n = baldes.length;
    const H = spec.altura || 132;
    const topo = 6;

    // Valor de cada série em cada balde, já empilhado quando for o caso.
    const bruto = spec.series.map((s) => baldes.map((b) => b[s.chave]));
    const desenho = [];
    if (spec.empilhado) {
      const acumulado = new Array(n).fill(0);
      for (const valores of bruto) {
        for (let i = 0; i < n; i++) acumulado[i] += valores[i] || 0;
        desenho.push([...acumulado]);
      }
    } else {
      for (const valores of bruto) desenho.push(valores);
    }

    let max = 0;
    for (const valores of desenho) {
      for (const v of valores) if (v !== null && v > max) max = v;
    }
    // Teto mínimo de 1: com todos os valores em zero, dividir por zero jogaria
    // a linha para NaN e o gráfico sairia vazio em vez de reto no chão.
    const teto = max || 1;

    const x = (i) => (n === 1 ? LARGURA_SVG / 2 : (i / (n - 1)) * LARGURA_SVG);
    const y = (v) => H - (v / teto) * (H - topo);

    // Grade em três linhas: chão, meio e teto. Mais que isso, num cartão de
    // 132px, vira hachura.
    const grade = [0, 0.5, 1]
      .map((f) => {
        const yy = (H - topo) * (1 - f) + topo;
        return (
          '<line class="grafico__grade" x1="0" x2="' +
          LARGURA_SVG +
          '" y1="' + yy + '" y2="' + yy + '" vector-effect="non-scaling-stroke"/>'
        );
      })
      .join('');

    // As séries empilhadas são desenhadas de cima para baixo: assim a de baixo
    // fica por último e não é encoberta pela vizinha.
    const ordem = spec.empilhado ? desenho.map((_, i) => i).reverse() : desenho.map((_, i) => i);

    const camadas = ordem
      .map((idx) => {
        const valores = desenho[idx];
        const serie = spec.series[idx];
        // Trecho contínuo por trecho contínuo: percentil sem amostra é `null`,
        // e ligar por cima do buraco desenharia uma reta entre dois dias que
        // não se encostam.
        const trechos = [];
        let atual = [];
        for (let i = 0; i < n; i++) {
          if (valores[i] === null || valores[i] === undefined) {
            if (atual.length) trechos.push(atual);
            atual = [];
          } else {
            atual.push(i);
          }
        }
        if (atual.length) trechos.push(atual);

        return trechos
          .map((is) => {
            const pontos = is.map((i) => x(i).toFixed(1) + ',' + y(valores[i]).toFixed(1));
            const linha =
              '<polyline class="grafico__linha" points="' +
              pontos.join(' ') +
              '" style="stroke:' +
              serie.cor +
              '"' +
              (serie.tracejada ? ' stroke-dasharray="6 4"' : '') +
              ' vector-effect="non-scaling-stroke"/>';

            if (spec.tipo !== 'area') return linha;

            // A área fecha no chão do gráfico. Com uma série só, o chão é o
            // eixo; empilhada, é a série de baixo - e é por isso que a de baixo
            // é desenhada por cima do preenchimento da de cima.
            const area =
              '<polygon class="grafico__preenchimento' +
              (spec.empilhado ? ' grafico__preenchimento--solido' : '') +
              '" points="' +
              x(is[0]).toFixed(1) + ',' + H + ' ' +
              pontos.join(' ') + ' ' +
              x(is[is.length - 1]).toFixed(1) + ',' + H +
              '" style="fill:' + serie.cor + '"/>';
            return area + linha;
          })
          .join('');
      })
      .join('');

    return {
      svg:
        '<svg class="grafico__svg" viewBox="0 0 ' +
        LARGURA_SVG +
        ' ' +
        H +
        '" preserveAspectRatio="none" aria-hidden="true">' +
        grade +
        camadas +
        '</svg>',
      teto,
      max,
    };
  }

  /**
   * Um cartão de gráfico completo: título, legenda, eixos e a camada de leitura.
   *
   * A legenda aparece a partir de DUAS séries e nunca antes: com uma só, o
   * título já a nomeia e a legenda seria uma linha a mais dizendo o que já
   * está escrito. Com duas ou mais ela é obrigatória - identidade de série não
   * pode ficar só na cor.
   */
  function graficoHtml(spec, baldes, balde) {
    const id = 'g' + proximoGrafico++;

    if (baldes.length === 0) {
      return '<div class="grafico"><div class="grafico__titulo">' + esc(spec.titulo) +
        '</div><p class="grafico__vazio">Sem período para mostrar.</p></div>';
    }

    // Percentil sem amostra é `null`, não zero: um gráfico de tempo de
    // atendimento sem nenhum atendimento não é "zero minuto", é "não houve".
    if (spec.exigeAmostra) {
      const temAlgum = baldes.some((b) =>
        spec.series.some((s) => b[s.chave] !== null && b[s.chave] !== undefined)
      );
      if (!temAlgum) {
        return '<div class="grafico"><div class="grafico__titulo">' + esc(spec.titulo) +
          '</div><p class="grafico__vazio">' + esc(spec.vazio || 'Sem dados no período.') +
          '</p></div>';
      }
    }

    const { svg, teto } = svgSerie(spec, baldes);
    graficos.set(id, { spec: spec, baldes: baldes, balde: balde });

    const legenda = spec.series.length > 1
      ? '<div class="grafico__legenda">' +
        spec.series.map((s) =>
          '<span class="grafico__chave" style="color:' + s.cor + '">' +
          '<span class="grafico__amostra' + (s.tracejada ? ' grafico__amostra--tracejada' : '') +
          '" style="background:' + (s.tracejada ? 'transparent' : s.cor) + '"></span>' +
          '<span style="color:var(--n300)">' + esc(s.nome) + '</span></span>'
        ).join('') +
        '</div>'
      : '';

    const eixoY = [teto, teto / 2, 0]
      .map((v) => '<span>' + esc(valorSerie(spec.formato === 'duracao' ? v : Math.round(v), spec.formato)) + '</span>')
      .join('');

    // Três marcas no eixo do tempo: começo, meio e fim. Com um rótulo por balde
    // eles se sobrepõem a partir de uns dez pontos.
    const meio = Math.floor((baldes.length - 1) / 2);
    const eixoX = (baldes.length > 2
      ? [0, meio, baldes.length - 1]
      : baldes.map((_, i) => i))
      .map((i) => '<span>' + esc(rotuloBalde(baldes[i].inicio, balde)) + '</span>')
      .join('');

    return '<div class="grafico' + (spec.alto ? ' grafico--alto' : '') + '" data-grafico="' + id + '">' +
      '<div class="grafico__titulo">' + esc(spec.titulo) + '</div>' +
      legenda +
      '<div class="grafico__area">' +
        '<div class="grafico__eixo-y">' + eixoY + '</div>' +
        '<div class="grafico__plot">' + svg +
          '<div class="grafico__cursor" hidden></div>' +
          '<div class="grafico__dica" hidden></div>' +
        '</div>' +
        // Dentro da grade, não depois dela: é o que alinha os rótulos do tempo
        // com o desenho sem chutar a largura da coluna do eixo Y.
        '<div class="grafico__eixo-x">' + eixoX + '</div>' +
      '</div>' +
    '</div>';
  }

  /**
   * Uma placa de indicador, com a faísca do próprio número ao fundo.
   *
   * `serie` é a chave do balde que a faísca desenha; sem ela a placa fica só com
   * o número. A faísca não tem eixo nem rótulo de propósito: ela responde "isso
   * está subindo ou descendo", e não "quanto exatamente" - para isso existem os
   * gráficos abaixo.
   */
  function statHtml(opcoes) {
    const cls = opcoes.tom ? ' stat--' + opcoes.tom : '';
    const ehTexto = typeof opcoes.valor === 'string';

    let spark = '';
    if (opcoes.serie && opcoes.serie.length > 1) {
      const H = 26;
      let max = 0;
      for (const v of opcoes.serie) if (v > max) max = v;
      const teto = max || 1;
      const pontos = opcoes.serie
        .map((v, i) => {
          const x = (i / (opcoes.serie.length - 1)) * 100;
          const y = H - 2 - (v / teto) * (H - 6);
          return x.toFixed(1) + ',' + y.toFixed(1);
        })
        .join(' ');
      spark =
        '<svg class="stat__spark" viewBox="0 0 100 ' + H + '" preserveAspectRatio="none" aria-hidden="true">' +
        '<polyline points="' + pontos + '" fill="none" stroke="rgba(255,255,255,.75)" ' +
        'stroke-width="1.5" vector-effect="non-scaling-stroke"/></svg>';
    }

    return '<div class="stat' + cls + '">' +
      '<div class="stat__rotulo">' + esc(opcoes.rotulo) + '</div>' +
      '<div class="stat__valor' + (ehTexto ? ' stat__valor--texto' : '') + '">' +
        esc(opcoes.valor) + '</div>' +
      (opcoes.nota ? '<div class="stat__nota">' + esc(opcoes.nota) + '</div>' : '') +
      spark +
    '</div>';
  }

  function secaoHtml(titulo, conteudo, cheia) {
    return '<details class="painel-secao" open><summary>' + esc(titulo) + '</summary>' +
      '<div class="painel-grade' + (cheia ? ' painel-grade--cheia' : '') + '">' +
      conteudo + '</div></details>';
  }

  // As cores das séries saem dos tokens do tema, lidos do CSS: assim a troca de
  // tema claro/escuro repinta os gráficos sem uma segunda tabela de cor aqui.
  function corToken(nome) {
    return getComputedStyle(document.documentElement).getPropertyValue(nome).trim();
  }

  function serieHtml(s, cfg) {
    const baldes = s.baldes;
    const balde = s.janela.balde;
    const a = corToken('--serie-a');
    const b = corToken('--serie-b');
    const f1 = corToken('--fila-1');
    const f2 = corToken('--fila-2');
    const f3 = corToken('--fila-3');
    const risco = corToken('--erro-linha');

    const fluxo = graficoHtml({
      titulo: 'Chamados abertos e resolvidos',
      tipo: 'linha',
      formato: 'inteiro',
      series: [
        { nome: 'Abertos', chave: 'aberturas', cor: a },
        { nome: 'Resolvidos', chave: 'resolucoes', cor: b },
      ],
    }, baldes, balde);

    const fila = graficoHtml({
      titulo: 'Fila no fim de cada período, por situação',
      tipo: 'area',
      formato: 'inteiro',
      empilhado: true,
      series: [
        { nome: 'A fazer', chave: 'filaAberto', cor: f1 },
        { nome: 'Em andamento', chave: 'filaEmAndamento', cor: f2 },
        { nome: 'Aguardando resposta', chave: 'filaAguardando', cor: f3 },
      ],
    }, baldes, balde);

    const atendimento = graficoHtml({
      titulo: 'Tempo até o 1º atendimento',
      tipo: 'linha',
      formato: 'duracao',
      exigeAmostra: true,
      vazio: 'Nenhum chamado foi atendido no período.',
      series: [
        { nome: 'Metade dos chamados (p50)', chave: 'atendimentoP50', cor: b },
        { nome: '9 de cada 10 (p90)', chave: 'atendimentoP90', cor: f3, tracejada: true },
      ],
    }, baldes, balde);

    const resolucao = graficoHtml({
      titulo: 'Tempo até resolver',
      tipo: 'linha',
      formato: 'duracao',
      exigeAmostra: true,
      vazio: 'Nenhum chamado foi resolvido no período.',
      series: [
        { nome: 'Metade dos chamados (p50)', chave: 'resolucaoP50', cor: b },
        { nome: '9 de cada 10 (p90)', chave: 'resolucaoP90', cor: f3, tracejada: true },
      ],
    }, baldes, balde);

    const mensagens = graficoHtml({
      titulo: 'Mensagens recebidas e enviadas',
      tipo: 'area',
      formato: 'inteiro',
      series: [
        { nome: 'Recebidas', chave: 'recebidas', cor: a },
        { nome: 'Enviadas', chave: 'enviadas', cor: b },
      ],
    }, baldes, balde);

    const outbox = graficoHtml({
      titulo: 'Mensagens esperando envio',
      tipo: 'area',
      formato: 'inteiro',
      series: [{ nome: 'Na fila de envio', chave: 'envioPendenteFim', cor: risco }],
    }, baldes, balde);

    const reab = graficoHtml({
      titulo: 'Reaberturas e cancelamentos',
      tipo: 'linha',
      formato: 'inteiro',
      series: [
        { nome: 'Reabertos', chave: 'reaberturas', cor: risco },
        { nome: 'Cancelados', chave: 'cancelamentos', cor: a },
      ],
    }, baldes, balde);

    return secaoHtml('Fila', fluxo + fila) +
      secaoHtml('Tempo de atendimento', atendimento + resolucao) +
      secaoHtml('Conversa no WhatsApp', mensagens + outbox) +
      secaoHtml('Retrabalho', reab, cfg && cfg.reabSozinha);
  }

  /** As dez placas do topo. */
  function placasHtml(s) {
    const a = s.agora;
    const d = s.desempenho;
    const baldes = s.baldes;
    const serie = (chave) => baldes.map((b) => b[chave] || 0);

    const totalPrazo = d.prazo.dentro + d.prazo.fora;
    const pctPrazo = totalPrazo > 0 ? Math.round((d.prazo.dentro / totalPrazo) * 100) : null;

    const abertos = serie('aberturas').reduce((x, y) => x + y, 0);
    const resolvidos = serie('resolucoes').reduce((x, y) => x + y, 0);

    return '<div class="stat-grid">' +
      // A fila é o número que diz quanto trabalho está no chão. Neutro porque
      // fila não é bom nem ruim em si - o que importa é para onde ela vai, e é
      // isso que a faísca mostra.
      statHtml({
        rotulo: 'Fila aberta', valor: a.fila, tom: 'neutro',
        serie: serie('filaFim'),
      }) +
      // Verde quando ninguém está esperando, âmbar quando está: aqui o número
      // ideal É zero, e a cor pode dizer isso.
      statHtml({
        rotulo: 'Aguardando 1º atendimento', valor: a.aguardandoPrimeiro,
        tom: a.aguardandoPrimeiro > 0 ? 'aviso' : 'ok',
      }) +
      // A placa de alarme, como na referência. Vermelha só quando há o que
      // alarmar - vermelho permanente deixa de ser visto.
      statHtml({
        rotulo: 'Prazo vencido', valor: a.vencidos,
        tom: a.vencidos > 0 ? 'erro' : 'ok',
        nota: a.venceEm24h > 0 ? a.venceEm24h + ' vencem em 24 h' : '',
      }) +
      statHtml({
        rotulo: 'Abertos no período', valor: abertos, tom: 'neutro',
        serie: serie('aberturas'),
      }) +
      statHtml({
        rotulo: 'Resolvidos no período', valor: resolvidos, tom: 'ok',
        serie: serie('resolucoes'),
      }) +
      statHtml({
        rotulo: 'Sem responsável', valor: a.semResponsavel,
        tom: a.semResponsavel > 0 ? 'aviso' : 'ok',
      }) +
      // Gente no meio do formulário do WhatsApp NESTE instante. É o número que
      // mostra que o bot está sendo usado agora, e não só que houve chamado.
      statHtml({
        rotulo: 'Conversas em andamento', valor: a.conversasEmAndamento, tom: 'neutro',
      }) +
      // Fila de envio crescendo = entrega de WhatsApp falhando. É operacional,
      // não de gestão, e é a razão de estar entre as placas: quando isso sobe,
      // nada mais no painel importa.
      statHtml({
        rotulo: 'Esperando envio', valor: a.envioPendente,
        tom: a.envioComFalha > 0 ? 'erro' : (a.envioPendente > 0 ? 'aviso' : 'ok'),
        nota: a.envioComFalha > 0 ? a.envioComFalha + ' com falha' : '',
        serie: serie('envioPendenteFim'),
      }) +
      // MEDIANA, não média: um chamado esquecido no fim de semana levanta a
      // média do período inteiro e não mexe na mediana.
      statHtml({
        rotulo: '1º atendimento (mediana)', valor: duracaoMin(d.atendimento.p50),
        tom: 'neutro',
        nota: d.atendimento.n > 0 ? d.atendimento.n + ' chamados' : 'sem amostra',
      }) +
      statHtml({
        rotulo: 'Resolvidos no prazo',
        valor: pctPrazo === null ? '—' : pctPrazo + '%',
        tom: pctPrazo === null ? 'neutro' : (pctPrazo >= 90 ? 'ok' : pctPrazo >= 70 ? 'aviso' : 'erro'),
        nota: totalPrazo > 0
          ? d.prazo.dentro + ' de ' + totalPrazo + ' com prazo'
          : 'nenhum resolvido com prazo',
      }) +
    '</div>';
  }

  /** A tabela por setor: o equivalente da tabela de nós da referência. */
  function tabelaSetorHtml(s) {
    if (s.porSetor.length === 0) return '';

    const linhas = s.porSetor.map((x) => {
      const total = x.dentro + x.fora;
      const pct = total > 0 ? Math.round((x.dentro / total) * 100) + '%' : '—';
      return '<tr>' +
        '<td>' + esc(x.rotulo) + '</td>' +
        '<td>' + x.fila + '</td>' +
        '<td>' + x.resolucoes + '</td>' +
        '<td>' + esc(duracaoMin(x.atendimentoP50)) + '</td>' +
        '<td>' + pct + amostraHtml(total) + '</td>' +
        '<td>' + (x.nota === null ? '—' : x.nota.toFixed(1)) + amostraHtml(x.notaN) + '</td>' +
      '</tr>';
    }).join('');

    // Os cabeçalhos dizem de que TEMPO cada coluna fala. "Fila" é agora,
    // "Resolvidos" é o período - e sem isso escrito a tabela mistura os dois
    // sem avisar.
    return '<div class="settings-label">Por setor</div>' +
      '<div class="metricas-rolagem"><table class="metricas-tabela">' +
        '<thead><tr><th>Setor</th><th>Fila agora</th><th>Resolvidos no período</th>' +
        '<th>1º atend. (mediana)</th><th>No prazo</th><th>Nota</th></tr></thead>' +
        '<tbody>' + linhas + '</tbody>' +
      '</table></div>';
  }

  function avaliacaoHtml(s) {
    const av = s.desempenho.avaliacao;
    if (av.n === 0) return '';

    const maior = Math.max.apply(null, av.distribuicao) || 1;
    const barras = av.distribuicao.map((qtd, i) =>
      '<div class="metrica-barra-linha">' +
        '<span class="metrica-barra-rotulo">' + (i + 1) + (i === 0 ? ' estrela' : ' estrelas') + '</span>' +
        '<span class="metrica-barra-trilha"><span class="metrica-barra-fill" style="width:' +
          Math.round((qtd / maior) * 100) + '%"></span></span>' +
        '<span class="metrica-barra-valor">' + qtd + '</span>' +
      '</div>'
    ).reverse().join('');

    // A distribuição e não só a média: 3,6 pode ser "todo mundo deu 4" ou
    // "metade deu 5 e alguém deu 1", e as duas pedem reação diferente.
    return '<div class="settings-label">Avaliação (média ' + av.media.toFixed(1) +
      ', ' + av.n + ' respostas)</div>' +
      '<div class="metrica-barras">' + barras + '</div>';
  }

  function metricasHtml(m, s) {
    // Leitura rápida de "onde está o atendimento", antes das tabelas detalhadas.
    // `porCategoria` já vem ordenada do servidor por `total` decrescente; um
    // teto de 8 barras mantém o gráfico legível — quem quer o resto tem as
    // tabelas logo abaixo. Barra proporcional ao maior total da lista, não ao
    // total geral: senão um único assunto dominante achataria todas as outras.
    const topAssuntos = m.porCategoria.slice(0, 8);
    const maiorTotal = topAssuntos.reduce((max, c) => Math.max(max, c.total), 0) || 1;
    const barras = topAssuntos.length
      ? '<div class="settings-label">Chamados por assunto</div>' +
        '<div class="metrica-barras">' +
        topAssuntos.map((c) =>
          '<div class="metrica-barra-linha">' +
            '<span class="metrica-barra-rotulo" title="' + esc(c.rotulo) + '">' + esc(c.rotulo) + '</span>' +
            '<span class="metrica-barra-trilha"><span class="metrica-barra-fill" style="width:' +
              Math.round((c.total / maiorTotal) * 100) + '%"></span></span>' +
            '<span class="metrica-barra-valor">' + c.total + '</span>' +
          '</div>'
        ).join('') +
        '</div>'
      : '';

    const distribuicao = barras + avaliacaoHtml(s) + tabelaSetorHtml(s) +
      // Três cortes do mesmo período. É o retorno dos campos de classificação:
      // assunto responde "sobre o que nos procuram", setor responde "quem está
      // atendendo", tipo separa a demanda interna da rede de franquias.
      tabelaMetricas('Por assunto', 'Assunto', m.porCategoria) +
      tabelaMetricas('Por tipo', 'Tipo', m.porTipo) +
      '<p class="modal__nota">As médias e medianas contam só os chamados que ' +
      'atingiram o marco; o número entre parênteses é o tamanho da amostra. ' +
      'Nas tabelas por assunto e por tipo a janela é pela data de ABERTURA do ' +
      'chamado, e o mesmo chamado aparece nas duas — uma vez em cada. Nos ' +
      'gráficos acima a janela é pela data do EVENTO: um chamado aberto na ' +
      'segunda e resolvido na quarta conta como abertura na segunda e como ' +
      'resolução na quarta.</p>';

    return placasHtml(s) +
      serieHtml(s) +
      secaoHtml('Distribuição', distribuicao, true);
  }

  /**
   * Recarrega o dashboard inteiro.
   *
   * Duas rotas em paralelo, e não uma: `/internal/metricas` agrupa o período por
   * assunto e tipo, `/internal/series` devolve a linha do tempo. São perguntas
   * de forma diferente (agregado x série), e juntá-las numa resposta faria
   * metade das chaves ignorar o balde e a outra metade depender dele.
   */
  async function atualizarMetricas() {
    const dias = Number(byId('metricas-periodo').value);
    const desde = dias > 0 ? new Date(Date.now() - dias * DIA).toISOString() : '';
    const corpo = byId('metricas-body');

    corpo.innerHTML = '<p class="metricas-vazio">Carregando…</p>';
    try {
      // O mapa de gráficos é reconstruído a cada carga: sem limpar, os ids da
      // carga anterior ficariam apontando para baldes de outro período e a
      // dica do cursor mostraria número de um gráfico que não está mais na tela.
      graficos.clear();
      proximoGrafico = 0;

      const [m, s] = await Promise.all([
        PainelApi.carregarMetricas(desde),
        PainelApi.carregarSerie(desde, ''),
      ]);
      corpo.innerHTML = metricasHtml(m, s);
    } catch (err) {
      corpo.innerHTML = '<p class="metricas-vazio">Não foi possível carregar: ' +
        esc(err.message) + '</p>';
    }
  }

  /**
   * A camada de leitura dos gráficos: linha vertical no cursor e caixa com os
   * valores do balde sob ele.
   *
   * Um listener só, delegado no corpo do dashboard, e não um por gráfico: os
   * cartões são recriados a cada troca de período, e listener por cartão
   * significaria religar tudo a cada carga (ou vazar os antigos).
   */
  function setupLeituraDeGraficos() {
    const corpo = byId('metricas-body');

    corpo.addEventListener('mousemove', (e) => {
      const plot = e.target.closest('.grafico__plot');
      if (!plot) return;

      const cartao = plot.closest('[data-grafico]');
      const dados = cartao && graficos.get(cartao.getAttribute('data-grafico'));
      if (!dados) return;

      const caixa = plot.getBoundingClientRect();
      const n = dados.baldes.length;
      // Ponto MAIS PRÓXIMO, e não o balde em que o cursor está: as marcas do
      // gráfico ficam nos extremos (0 e 100% da largura), então dividir a
      // largura em n faixas iguais desalinharia a dica do ponto desenhado.
      const frac = Math.min(Math.max((e.clientX - caixa.left) / caixa.width, 0), 1);
      const i = n === 1 ? 0 : Math.round(frac * (n - 1));
      const b = dados.baldes[i];

      // Trocou de gráfico sem passar pelo lado de fora: apaga o anterior antes,
      // senão as duas dicas ficam abertas.
      if (leituraAberta && leituraAberta !== plot) esconderLeitura();
      leituraAberta = plot;

      const cursor = plot.querySelector('.grafico__cursor');
      const dica = plot.querySelector('.grafico__dica');
      const x = n === 1 ? caixa.width / 2 : (i / (n - 1)) * caixa.width;

      cursor.style.left = x + 'px';
      cursor.hidden = false;

      dica.innerHTML = '<strong>' + esc(rotuloBalde(b.inicio, dados.balde)) + '</strong><dl>' +
        dados.spec.series.map((sr) =>
          '<dt><span class="grafico__amostra" style="background:' + sr.cor + '"></span>' +
          esc(sr.nome) + '</dt><dd>' + esc(valorSerie(b[sr.chave], dados.spec.formato)) + '</dd>'
        ).join('') +
        '</dl>';
      dica.hidden = false;

      // A caixa vira de lado ao chegar na borda: fixa à esquerda, ela sairia
      // cortada pelo `overflow` do corpo do dashboard nos últimos baldes.
      const largura = dica.offsetWidth;
      const esquerda = x + 12 + largura > caixa.width ? x - 12 - largura : x + 12;
      dica.style.left = Math.max(0, esquerda) + 'px';
      dica.style.top = '4px';
    });

    // `mouseleave` no corpo e não no plot: saindo do gráfico por cima da dica, o
    // `mouseout` do plot não dispara e a caixa ficaria pregada na tela.
    corpo.addEventListener('mouseleave', esconderLeitura);
    corpo.addEventListener('mousemove', (e) => {
      if (!e.target.closest('.grafico__plot')) esconderLeitura();
    });
  }

  // Guardado num nó só: `esconderLeitura` roda a cada movimento do mouse fora
  // de um gráfico, e varrer o documento inteiro nessa frequência é trabalho
  // jogado fora quando não há nada aberto.
  let leituraAberta = null;

  function esconderLeitura() {
    if (!leituraAberta) return;
    leituraAberta.querySelector('.grafico__cursor').hidden = true;
    leituraAberta.querySelector('.grafico__dica').hidden = true;
    leituraAberta = null;
  }

  function setupDashboard() {
    byId('metricas-periodo').addEventListener('change', atualizarMetricas);
    setupLeituraDeGraficos();

    // Os gráficos leem a cor das séries dos tokens do CSS na hora de desenhar,
    // então o SVG já pintado não acompanha a troca de tema. Redesenhar é o
    // caminho honesto: o alternativo seria `stroke="currentColor"` com uma
    // classe por série, o que espalharia a paleta dos gráficos por mais um
    // lugar.
    if (window.PainelTema) {
      window.PainelTema.aoMudar(() => {
        if (byId('view-dashboard').classList.contains('is-active')) atualizarMetricas();
      });
    }
  }

  /* ---------- Assuntos (árvore de categorias) --------------------------- */

  let assuntosAberto = false;

  function mostrarErroAssunto(mensagem) {
    const el = byId('assuntos-erro');
    el.textContent = mensagem;
    el.hidden = !mensagem;
  }

  /** Pais possíveis: qualquer assunto menos o próprio nó e o que está abaixo dele. */
  function preencherSelectPai(sel, assuntoId, selecionadoId) {
    const proibidos = descendentesDe(assuntoId);
    const linhas = assuntosEmArvore().filter((n) => proibidos.indexOf(n.assunto.id) === -1);

    sel.innerHTML =
      '<option value=""' + (!selecionadoId ? ' selected' : '') + '>— raiz —</option>' +
      linhas.map((n) => opcaoAssunto(n, selecionadoId)).join('');
  }

  /**
   * Uma linha do modal de assuntos.
   *
   * O interruptor "No WhatsApp" é o que define o ASSUNTO DE USO INTERNO:
   * desmarcado, o assunto sai do menu da conversa e continua no seletor de
   * classificação do painel. É um interruptor SEPARADO de "Ativo" porque as duas
   * perguntas são diferentes — "o assunto existe?" e "o cliente pode escolhê-lo?"
   * — e juntá-las custaria exatamente o caso que motivou isto: o assunto vivo,
   * usado todo dia pela equipe, que o cliente nunca deve ver.
   *
   * Numa FILHA de um assunto interno o interruptor aparece desligado e travado.
   * Não é a coluna dela que está `false` (o servidor não mexe nas filhas, para
   * religar o pai devolver o ramo inteiro) — é que a conversa desce um nível por
   * vez, e um pai que nunca é oferecido torna a subárvore inalcançável. Mostrar
   * a filha como "no WhatsApp" seria mentir na tela; deixar o interruptor
   * clicável prometeria um efeito que não existe enquanto o pai estiver interno.
   */
  function assuntoRowHtml(no) {
    const a = no.assunto;
    const uso = a.chamados === 1 ? '1 chamado' : a.chamados + ' chamados';
    const fora = foraDoMenu(a);
    const herdado = fora === 'herdado';

    return '<div class="assunto-row' + (no.nivel > 0 ? ' assunto-row--filha' : '') +
      (a.ativa ? '' : ' is-inativa') + (fora ? ' is-interna' : '') +
      '" data-assunto="' + a.id + '">' +
      '<div class="assunto-row__ident">' +
        '<input class="assunto-row__rotulo" type="text" maxlength="120" ' +
          'value="' + esc(a.rotulo) + '" aria-label="Nome de exibição">' +
        '<input class="assunto-row__nome" type="text" maxlength="120" ' +
          'value="' + esc(a.nome) + '" aria-label="Nome interno">' +
        '<span class="assunto-row__codigo">' + esc(a.codigo) + ' · ' + esc(uso) +
          (fora ? ' · <span class="assunto-row__interno">' +
            (herdado ? 'interno (o assunto acima está fora do menu)' : 'só uso interno') +
            '</span>' : '') +
        '</span>' +
      '</div>' +
      '<select class="select assunto-row__pai" aria-label="Dentro de"></select>' +
      '<input class="modal__num assunto-row__ordem" type="number" min="0" max="9999" ' +
        'value="' + a.ordem + '" aria-label="Posição no menu">' +
      '<label class="conn-toggle" title="' +
        (herdado
          ? 'Herdado: o assunto acima está marcado como de uso interno.'
          : 'Desmarque para o assunto sair do menu do WhatsApp e ficar só para a TI.') +
        '"><input type="checkbox" class="assunto-row__whats"' +
        (fora ? '' : ' checked') + (herdado ? ' disabled' : '') +
        '><span>No WhatsApp</span></label>' +
      '<label class="conn-toggle"><input type="checkbox" class="assunto-row__ativa"' +
        (a.ativa ? ' checked' : '') + '><span>Ativo</span></label>' +
      '<button class="icon-btn person-row__remove assunto-row__remove" ' +
        'aria-label="Excluir ' + esc(a.rotulo) + '">' + TRASH_ICON + '</button>' +
    '</div>';
  }

  function renderAssuntos() {
    const corpo = byId('assuntos-body');
    const arvore = assuntosEmArvore();

    corpo.innerHTML = arvore.length
      ? arvore.map(assuntoRowHtml).join('')
      : '<p class="metricas-vazio">Nenhum assunto cadastrado — o bot vai pular ' +
        'essa pergunta e ir direto ao nome.</p>';

    preencherSelectPai(byId('assunto-novo-pai'), null, null);
    bindAssuntos();
  }

  function bindAssuntos() {
    byId('assuntos-body').querySelectorAll('.assunto-row').forEach((row) => {
      const id = Number(row.dataset.assunto);
      const a = assuntosPorId[id];
      if (!a) return;

      const paiSel = row.querySelector('.assunto-row__pai');
      preencherSelectPai(paiSel, id, a.paiId);

      // `change` e não `input`: `input` dispara a cada tecla, e isso seria um
      // PATCH por letra digitada no rótulo.
      row.querySelector('.assunto-row__rotulo').addEventListener('change', (e) =>
        salvarAssunto(id, { rotulo: e.target.value.trim() })
      );
      row.querySelector('.assunto-row__nome').addEventListener('change', (e) =>
        salvarAssunto(id, { nome: e.target.value.trim() })
      );
      row.querySelector('.assunto-row__ordem').addEventListener('change', (e) =>
        salvarAssunto(id, { ordem: Math.max(0, parseInt(e.target.value, 10) || 0) })
      );
      paiSel.addEventListener('change', (e) =>
        salvarAssunto(id, { paiId: e.target.value === '' ? null : Number(e.target.value) })
      );
      row.querySelector('.assunto-row__ativa').addEventListener('change', (e) =>
        salvarAssunto(id, { ativa: e.target.checked })
      );
      // Na filha de um assunto interno o campo vem `disabled`, e `change` nunca
      // dispara — o ouvinte é registrado do mesmo jeito porque o `disabled` sai
      // sozinho na próxima renderização, assim que o pai volta ao menu.
      row.querySelector('.assunto-row__whats').addEventListener('change', (e) =>
        salvarAssunto(id, { visivelNoWhatsapp: e.target.checked })
      );
      row.querySelector('.assunto-row__remove').addEventListener('click', () => removerAssunto(a));
    });
  }

  /**
   * Manda SÓ o campo que mudou.
   *
   * O servidor trata campo ausente como "não mexa" e `paiId: null` como "promova
   * para raiz"; mandar o objeto inteiro apagaria essa distinção. Em qualquer
   * falha a lista é redesenhada a partir do servidor, o que desfaz na tela o que
   * não foi aceito - um ciclo recusado, por exemplo, não pode ficar parecendo
   * salvo.
   */
  async function salvarAssunto(id, mudancas) {
    mostrarErroAssunto('');
    try {
      await PainelApi.atualizarAssunto(id, mudancas);
      await carregarAssuntos();
      renderAssuntos();
      render(); // o chip do cartão pode ter mudado de texto
    } catch (err) {
      mostrarErroAssunto(err.message);
      renderAssuntos();
    }
  }

  async function adicionarAssunto() {
    const codigo = byId('assunto-novo-codigo').value.trim().toLowerCase();
    const nome = byId('assunto-novo-nome').value.trim();
    // Sem rótulo próprio, o nome interno serve: é o caso comum (metade dos
    // assuntos da empresa tem os dois iguais).
    const rotulo = byId('assunto-novo-rotulo').value.trim() || nome;
    const pai = byId('assunto-novo-pai').value;
    // Marcado por padrão no HTML: o assunto comum é o de atendimento, e interno
    // é a exceção que precisa ser dita — a mesma escolha do `default` do servidor.
    const noWhatsapp = byId('assunto-novo-whats').checked;

    // Mesmas regras do schema no servidor. Conferir aqui é conforto, não
    // garantia: quem recusa de verdade é o POST.
    if (!/^[a-z0-9_]{2,60}$/.test(codigo)) {
      return mostrarErroAssunto(
        'O código aceita só letras minúsculas, números e _ — por exemplo, trocas_devolucoes.'
      );
    }
    if (nome.length < 2) {
      return mostrarErroAssunto('O nome interno precisa de ao menos 2 caracteres.');
    }

    const botao = byId('assunto-add');
    botao.disabled = true;
    try {
      await PainelApi.criarAssunto({
        codigo: codigo,
        nome: nome,
        rotulo: rotulo,
        visivelNoWhatsapp: noWhatsapp,
        paiId: pai === '' ? null : Number(pai),
      });

      byId('assunto-novo-codigo').value = '';
      byId('assunto-novo-nome').value = '';
      byId('assunto-novo-rotulo').value = '';
      byId('assunto-novo-whats').checked = true;
      mostrarErroAssunto('');
      await carregarAssuntos();
      renderAssuntos();
      showToast(
        noWhatsapp
          ? 'Assunto adicionado — já vale no próximo menu do WhatsApp'
          : 'Assunto adicionado só para uso interno — não entra no menu do WhatsApp'
      );
    } catch (err) {
      mostrarErroAssunto(err.message);
    } finally {
      botao.disabled = false;
    }
  }

  /**
   * Excluir, ou desativar quando excluir destruiria histórico.
   *
   * O servidor recusa o DELETE de um assunto em uso (409). Em vez de mostrar o
   * erro e deixar a pessoa sem saída, a pergunta já oferece o que ela realmente
   * quer: tirar do menu sem perder os chamados que somam por ele no resumo.
   */
  async function removerAssunto(a) {
    if (a.chamados > 0) {
      const pergunta = a.chamados + ' chamado(s) usam "' + (a.rotulo || 'este assunto') +
        '", então ele não pode ser excluído sem perder esse histórico.\n\n' +
        'Deseja DESATIVÁ-LO? Ele sai do menu do WhatsApp e continua somando no resumo.';
      if (!window.confirm(pergunta)) return;
      return salvarAssunto(a.id, { ativa: false });
    }

    if (!window.confirm('Excluir o assunto "' + (a.rotulo || 'sem nome') + '"?')) return;

    mostrarErroAssunto('');
    try {
      await PainelApi.excluirAssunto(a.id);
      await carregarAssuntos();
      renderAssuntos();
      render();
      showToast('Assunto excluído');
    } catch (err) {
      mostrarErroAssunto(err.message);
    }
  }

  async function openAssuntos() {
    if (!PainelApi.temToken()) {
      showToast('Informe o token do painel antes de editar os assuntos');
      return;
    }
    assuntosAberto = true;
    mostrarErroAssunto('');
    byId('assuntos-modal').classList.add('is-open');
    byId('assuntos-modal').setAttribute('aria-hidden', 'false');
    byId('assuntos-backdrop').classList.add('is-open');

    // Relê antes de mostrar: outro atendente pode ter mexido desde a última carga,
    // e editar em cima de uma foto velha é como duas pessoas sobrescrevem uma à
    // outra sem perceber.
    await carregarAssuntos();
    renderAssuntos();
  }

  function closeAssuntos() {
    assuntosAberto = false;
    byId('assuntos-modal').classList.remove('is-open');
    byId('assuntos-modal').setAttribute('aria-hidden', 'true');
    byId('assuntos-backdrop').classList.remove('is-open');
  }

  function setupAssuntos() {
    byId('assuntos-backdrop').addEventListener('click', closeAssuntos);
    byId('assuntos-close').addEventListener('click', closeAssuntos);
    byId('assuntos-done').addEventListener('click', closeAssuntos);
    byId('assunto-add').addEventListener('click', adicionarAssunto);
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && assuntosAberto) closeAssuntos();
    });
  }

  /**
   * Troca entre as duas visões de página (Chamados/Dashboard). Mesmo padrão de
   * show/hide que os modais já usam com `.is-open`, só que numa `section`
   * (`.view`) em vez de modal — Dashboard deixou de ser modal para virar visão
   * própria, alcançável pela barra lateral.
   */
  let viewAtual = 'chamados';

  function mudarView(nome) {
    if (nome === viewAtual) return;
    viewAtual = nome;
    byId('view-chamados').classList.toggle('is-active', nome === 'chamados');
    byId('view-dashboard').classList.toggle('is-active', nome === 'dashboard');

    if (nome === 'dashboard') {
      if (!PainelApi.temToken()) {
        byId('metricas-body').innerHTML =
          '<p class="metricas-vazio">Informe o token do painel para ver o dashboard.</p>';
        return;
      }
      atualizarMetricas();
    }
  }

  /* ---------- Setores (áreas da empresa) ------------------------------- */

  let setoresAberto = false;

  function mostrarErroSetor(mensagem) {
    const el = byId('setores-erro');
    el.textContent = mensagem;
    el.hidden = !mensagem;
  }

  function setorRowHtml(x) {
    // Os dois usos aparecem somados e detalhados: é o número que explica por que
    // o servidor recusa o DELETE, e "3 como origem" é uma informação diferente de
    // "3 atendidos" para quem está decidindo se pode excluir.
    const usos = x.chamados + x.origens;
    // `uso` e não `detalhe`: aquele nome já é a variável de módulo que guarda as
    // listas do chamado aberto, e sombreá-la aqui era um convite a confusão na
    // próxima leitura deste arquivo.
    const uso = usos === 0
      ? 'sem chamados'
      : usos + ' chamado(s) · ' + x.chamados + ' atendendo, ' + x.origens + ' abertos por ele';

    return '<div class="assunto-row' + (x.ativo ? '' : ' is-inativa') +
      '" data-setor="' + x.id + '">' +
      '<div class="assunto-row__ident">' +
        '<input class="assunto-row__rotulo setor-row__nome" type="text" maxlength="120" ' +
          'value="' + esc(x.nome) + '" aria-label="Nome do setor">' +
        '<span class="assunto-row__codigo">' + esc(x.codigo) + ' · ' + esc(uso) + '</span>' +
      '</div>' +
      '<input class="modal__num setor-row__ordem" type="number" min="0" max="9999" ' +
        'value="' + x.ordem + '" aria-label="Posição na lista">' +
      '<label class="conn-toggle"><input type="checkbox" class="setor-row__ativo"' +
        (x.ativo ? ' checked' : '') + '><span>Ativo</span></label>' +
      '<button class="icon-btn person-row__remove setor-row__remove" ' +
        'aria-label="Excluir ' + esc(x.nome) + '">' + TRASH_ICON + '</button>' +
    '</div>';
  }

  function renderSetores() {
    const corpo = byId('setores-body');
    const lista = ordenarSetores(setores);

    corpo.innerHTML = lista.length
      ? lista.map(setorRowHtml).join('')
      : '<p class="metricas-vazio">Nenhum setor cadastrado — os seletores de setor ' +
        'ficam vazios até o primeiro ser criado.</p>';

    bindSetores();
  }

  function bindSetores() {
    byId('setores-body').querySelectorAll('[data-setor]').forEach((row) => {
      const id = Number(row.dataset.setor);
      const x = setoresPorId[id];
      if (!x) return;

      // `change` e não `input`, pelo mesmo motivo dos assuntos: `input` dispara a
      // cada tecla, e isso seria um PATCH por letra digitada.
      row.querySelector('.setor-row__nome').addEventListener('change', (e) =>
        salvarSetor(id, { nome: e.target.value.trim() })
      );
      row.querySelector('.setor-row__ordem').addEventListener('change', (e) =>
        salvarSetor(id, { ordem: Math.max(0, parseInt(e.target.value, 10) || 0) })
      );
      row.querySelector('.setor-row__ativo').addEventListener('change', (e) =>
        salvarSetor(id, { ativo: e.target.checked })
      );
      row.querySelector('.setor-row__remove').addEventListener('click', () => removerSetor(x));
    });
  }

  /**
   * Manda só o campo que mudou, e redesenha a partir do servidor em qualquer
   * falha - o que desfaz na tela o que não foi aceito.
   *
   * `render()` no fim porque o nome do setor aparece NO CARTÃO: renomear aqui
   * precisa repintar o quadro, senão os cartões ficam com o nome velho até a
   * próxima carga.
   */
  async function salvarSetor(id, mudancas) {
    mostrarErroSetor('');
    try {
      await PainelApi.atualizarSetor(id, mudancas);
      await carregarSetores();
      renderSetores();
      render();
    } catch (err) {
      mostrarErroSetor(err.message);
      renderSetores();
    }
  }

  async function adicionarSetor() {
    const codigo = byId('setor-novo-codigo').value.trim().toLowerCase();
    const nome = byId('setor-novo-nome').value.trim();

    // Mesmas regras do servidor. Conferir aqui é conforto, não garantia: quem
    // recusa de verdade é o POST.
    if (!/^[a-z0-9_]{2,60}$/.test(codigo)) {
      return mostrarErroSetor(
        'O código aceita só letras minúsculas, números e _ — por exemplo, pos_venda.'
      );
    }
    if (nome.length < 2) return mostrarErroSetor('O nome precisa de ao menos 2 caracteres.');

    const botao = byId('setor-add');
    botao.disabled = true;
    try {
      await PainelApi.criarSetor({ codigo: codigo, nome: nome });
      byId('setor-novo-codigo').value = '';
      byId('setor-novo-nome').value = '';
      mostrarErroSetor('');
      await carregarSetores();
      renderSetores();
      showToast('Setor adicionado');
    } catch (err) {
      mostrarErroSetor(err.message);
    } finally {
      botao.disabled = false;
    }
  }

  /**
   * Excluir, ou desativar quando excluir destruiria histórico.
   *
   * Mesmo desenho de `removerAssunto`: o servidor recusa o DELETE de um setor em
   * uso (409), e mostrar só o erro deixaria a pessoa sem saída. A pergunta já
   * oferece o que ela realmente quer - tirar dos seletores sem perder os
   * chamados que somam por ele no resumo.
   */
  async function removerSetor(x) {
    const usos = x.chamados + x.origens;

    if (usos > 0) {
      const pergunta = usos + ' chamado(s) apontam para "' + x.nome +
        '", então ele não pode ser excluído sem perder esse histórico.\n\n' +
        'Deseja DESATIVÁ-LO? Ele sai dos seletores e continua somando no resumo.';
      if (!window.confirm(pergunta)) return;
      return salvarSetor(x.id, { ativo: false });
    }

    if (!window.confirm('Excluir o setor "' + x.nome + '"?')) return;

    mostrarErroSetor('');
    try {
      await PainelApi.excluirSetor(x.id);
      await carregarSetores();
      renderSetores();
      render();
      showToast('Setor excluído');
    } catch (err) {
      mostrarErroSetor(err.message);
    }
  }

  async function openSetores() {
    if (!PainelApi.temToken()) {
      showToast('Informe o token do painel antes de editar os setores');
      return;
    }
    setoresAberto = true;
    mostrarErroSetor('');
    byId('setores-modal').classList.add('is-open');
    byId('setores-modal').setAttribute('aria-hidden', 'false');
    byId('setores-backdrop').classList.add('is-open');

    // Relê antes de desenhar: outro atendente pode ter mexido na lista desde a
    // última carga, e editar em cima de uma foto velha é como duas telas
    // discordam.
    await carregarSetores();
    renderSetores();
  }

  function closeSetores() {
    setoresAberto = false;
    byId('setores-modal').classList.remove('is-open');
    byId('setores-modal').setAttribute('aria-hidden', 'true');
    byId('setores-backdrop').classList.remove('is-open');
  }

  function setupSetores() {
    byId('setores-backdrop').addEventListener('click', closeSetores);
    byId('setores-close').addEventListener('click', closeSetores);
    byId('setores-done').addEventListener('click', closeSetores);
    byId('setor-add').addEventListener('click', adicionarSetor);
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && setoresAberto) closeSetores();
    });
  }

  /**
   * O botão de tema.
   *
   * A troca em si e a persistência são do `tema.js`, que roda no <head> antes
   * do paint — este arquivo só liga o clique e mantém o texto acessível em dia.
   * O ÍCONE não passa por aqui: quem decide qual dos dois aparece é o CSS, pelo
   * `data-theme` do <html>.
   *
   * `PainelTema.aoMudar` também dispara quando a troca vem do SISTEMA (enquanto
   * ninguém escolheu à mão), e é por isso que o rótulo é atualizado por callback
   * em vez de dentro do clique: alguém que muda o Windows para escuro às 18h
   * veria o botão dizer "mudar para escuro" com a tela já escura.
   */
  function setupTema() {
    const botao = byId('tema-toggle');
    if (!botao || !window.PainelTema) return;

    const rotular = (tema) => {
      const proximo = tema === 'dark' ? 'claro' : 'escuro';
      botao.setAttribute('aria-label', `Mudar para o tema ${proximo}`);
      botao.title = `Mudar para o tema ${proximo}`;
    };

    rotular(window.PainelTema.aplicado());
    window.PainelTema.aoMudar(rotular);
    botao.addEventListener('click', () => window.PainelTema.alternar());
  }

  function setupChrome() {
    const menuToggle = byId('menu-toggle');
    menuToggle.addEventListener('click', () => {
      const collapsed = document.querySelector('.sidebar').classList.toggle('is-collapsed');
      menuToggle.setAttribute('aria-expanded', String(!collapsed));
    });

    setupTema();

    bindSearch('global-search', 'filter-text');

    // "Nova atividade" saiu da barra do quadro (chamado nasce no WhatsApp); o
    // "Criar" do topo continua lá e explica isso ao ser clicado.
    byId('create-issue').addEventListener('click', createIssue);

    const sidebar = document.querySelector('.sidebar');
    sidebar.addEventListener('click', (e) => {
      const item = e.target.closest('.sidebar__item');
      if (!item) return;
      e.preventDefault();
      sidebar.querySelectorAll('.sidebar__item').forEach((el) => {
        el.classList.remove('is-active');
        el.removeAttribute('aria-current');
      });
      item.classList.add('is-active');
      item.setAttribute('aria-current', 'page');
      const label = item.textContent.trim();
      if (label === 'Dashboard') mudarView('dashboard');
      else if (label === 'Chamados') mudarView('chamados');
      else if (label === 'Assuntos') openAssuntos();
      else if (label === 'Setores') openSetores();
      else if (label === 'Pessoas') openPeople();
      else if (label === 'Configurações do projeto') openSettings();
      else showToast(`Seção "${label}" ainda não disponível`);
    });

    // Botões decorativos: dão retorno visível sem uma ação real associada.
    document.addEventListener('click', (e) => {
      const el = e.target.closest('[data-soon]');
      if (el) showToast(el.getAttribute('data-soon'));
    });
  }

  /* ---------- Pessoas (equipe) ---------------------------------------- */

  // A mesma paleta de `CORES_SOLICITANTE` — ver o comentário lá para o porquê
  // de serem oito e não dez.
  const PERSON_COLORS = [
    '#96421C', '#4C3BA8', '#8A5000', '#3B3F8F',
    '#3D6B33', '#5E4B8B', '#7A3E12', '#0F6068',
  ];

  let peopleOpen = false;

  const TRASH_ICON = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" ' +
    'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
    '<path d="M3 6h18M8 6V4h8v2M6 6l1 14h10l1-14"/></svg>';

  function personRowHtml(person) {
    return `<div class="person-row" data-person="${person.id}">` +
      `<span class="avatar person-row__avatar" style="background:${esc(person.color)}">${esc(initials(person.name))}</span>` +
      `<input class="person-row__name" type="text" value="${esc(person.name)}" aria-label="Nome de exibição">` +
      `<input class="person-row__color" type="color" value="${esc(person.color)}" aria-label="Cor">` +
      `<button class="icon-btn person-row__remove" aria-label="Remover ${esc(person.name)}">${TRASH_ICON}</button>` +
    '</div>';
  }

  function renderPeople() {
    byId('people-body').innerHTML = people.map(personRowHtml).join('');
    bindPeople();
  }

  function bindPeople() {
    byId('people-body').querySelectorAll('.person-row').forEach((row) => {
      const person = peopleById[row.dataset.person];
      if (!person) return;
      const avatarEl = row.querySelector('.person-row__avatar');

      // Nome e cor atualizam ao vivo sem reconstruir a lista (preserva o foco).
      row.querySelector('.person-row__name').addEventListener('input', (e) => {
        person.name = e.target.value;
        avatarEl.textContent = initials(person.name);
        render();
        renderAvatarGroup();
        agendarGravacao(person);
      });
      row.querySelector('.person-row__color').addEventListener('input', (e) => {
        person.color = e.target.value;
        avatarEl.style.background = person.color;
        render();
        renderAvatarGroup();
        agendarGravacao(person);
      });
      row.querySelector('.person-row__remove').addEventListener('click', () => removePerson(person));
    });
  }

  /**
   * Grava a linha no banco depois que a digitação para.
   *
   * O evento `input` dispara a cada tecla: renomear "Ana" sem espera seriam três
   * PATCHs, e nada garante que cheguem na ordem em que saíram - o quadro podia
   * acabar gravando "An". Meio segundo depois da última tecla é uma escrita só.
   *
   * O timer é por pessoa: editar duas linhas seguidas não pode fazer a segunda
   * cancelar a gravação da primeira.
   */
  const ESPERA_GRAVACAO_MS = 500;
  const gravacoesPendentes = {};

  function agendarGravacao(person) {
    clearTimeout(gravacoesPendentes[person.id]);
    gravacoesPendentes[person.id] = setTimeout(async () => {
      delete gravacoesPendentes[person.id];
      try {
        await PainelApi.atualizarPessoa(person.id, { nome: person.name, cor: person.color });
      } catch (err) {
        showToast('Não foi possível salvar ' + (person.name || 'a pessoa') + ': ' + err.message);
      }
    }, ESPERA_GRAVACAO_MS);
  }

  /**
   * A pessoa nasce no BANCO e só então aparece na tela.
   *
   * Sem o id do servidor não haveria para onde mandar a primeira renomeação, e
   * duas abas criariam linhas diferentes achando que eram a mesma. É por isso
   * que isto espera a resposta em vez de desenhar otimista como o arrastar de
   * cartão faz: lá o id já existe; aqui é ele que está sendo criado.
   */
  async function addPerson() {
    const cor = PERSON_COLORS[people.length % PERSON_COLORS.length];

    let criada;
    try {
      criada = await PainelApi.criarPessoa({ nome: '', cor: cor });
    } catch (err) {
      showToast('Não foi possível adicionar: ' + err.message);
      return;
    }

    const person = { id: criada.id, name: criada.nome, color: criada.cor };
    people.push(person);
    peopleById[person.id] = person;
    renderPeople();
    render();
    renderAvatarGroup();
    const rows = byId('people-body').querySelectorAll('.person-row');
    rows[rows.length - 1].querySelector('.person-row__name').focus();
  }

  async function removePerson(person) {
    if (!window.confirm(`Remover ${person.name || 'esta pessoa'}?`)) return;

    // Uma renomeação ainda pendente cairia num PATCH para uma linha que acabou
    // de deixar de existir: 404 e um aviso na tela sem nada de errado ter
    // acontecido.
    clearTimeout(gravacoesPendentes[person.id]);
    delete gravacoesPendentes[person.id];

    try {
      await PainelApi.excluirPessoa(person.id);
    } catch (err) {
      showToast('Não foi possível remover: ' + err.message);
      return;
    }

    const idx = people.indexOf(person);
    if (idx > -1) people.splice(idx, 1);
    delete peopleById[person.id];
    issues.forEach((issue) => {
      if (issue.assignee === person.id) issue.assignee = null;
    });
    if (filters.assignee === person.id) filters.assignee = null;
    renderPeople();
    render();
    renderAvatarGroup();
    showToast(`${person.name || 'Pessoa'} removida`);
  }

  function openPeople() {
    peopleOpen = true;
    renderPeople();
    byId('people-modal').classList.add('is-open');
    byId('people-modal').setAttribute('aria-hidden', 'false');
    byId('people-backdrop').classList.add('is-open');
  }

  function closePeople() {
    peopleOpen = false;
    byId('people-modal').classList.remove('is-open');
    byId('people-modal').setAttribute('aria-hidden', 'true');
    byId('people-backdrop').classList.remove('is-open');
  }

  function setupPeople() {
    byId('people-backdrop').addEventListener('click', closePeople);
    byId('people-close').addEventListener('click', closePeople);
    byId('people-done').addEventListener('click', closePeople);
    byId('people-add').addEventListener('click', addPerson);
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && peopleOpen) closePeople();
    });
  }

  /* ---------- Configurações ------------------------------------------- */

  let settingsOpen = false;
  /* ---------- Configuração do painel (banco) --------------------------- */

  /**
   * A configuração vem do BANCO, não do navegador.
   *
   * Antes ela vivia no `localStorage`, e era a última coisa ajustável na tela
   * que cada navegador guardava só para si — dois atendentes na mesma
   * instalação viam nomes de projeto diferentes, sem forma de saber qual era o
   * certo. Assuntos, setores e pessoas já tinham migrado; isto fechou a conta.
   *
   * A tradução entre o vocabulário da tela (`sprint`, `sprintRange`,
   * `daysRemaining`, vindos do quadro genérico) e o da API (`periodoRotulo`,
   * `periodoTexto`, `diasRestantes`) acontece só aqui, nestas duas funções -
   * pelo mesmo motivo de `paraCartao`: duas traduções espalhadas divergem.
   */
  async function carregarConfiguracao() {
    if (!PainelApi.temToken()) return;
    try {
      const c = await PainelApi.carregarConfiguracao();
      project.name = c.nome;
      project.key = c.sigla;
      project.sprint = c.periodoRotulo;
      project.sprintRange = c.periodoTexto;
      project.daysRemaining = c.diasRestantes;

      renderHeader();
    } catch (err) {
      showToast('Não foi possível carregar a configuração: ' + err.message);
    }
  }

  // Um timer por campo: editar nome e sigla em seguida não pode fazer o segundo
  // cancelar a gravação do primeiro.
  const configPendente = {};

  function agendarSalvarConfig(mudancas) {
    Object.entries(mudancas).forEach(([campo, valor]) => {
      clearTimeout(configPendente[campo]);
      configPendente[campo] = setTimeout(async () => {
        delete configPendente[campo];
        try {
          await PainelApi.salvarConfiguracao({ [campo]: valor });
        } catch (err) {
          showToast('Não foi possível salvar a configuração: ' + err.message);
        }
      }, ESPERA_GRAVACAO_MS);
    });
  }

  function bindSettingsFields() {
    const wire = (id, apply) => {
      byId(id).addEventListener('input', (e) => {
        const mudanca = apply(e.target.value);
        renderHeader();
        agendarSalvarConfig(mudanca);
      });
    };
    wire('set-name', (v) => { project.name = v; return { nome: v }; });
    wire('set-key', (v) => { project.key = v; return { sigla: v }; });
    wire('set-sprint', (v) => { project.sprint = v; return { periodoRotulo: v }; });
    wire('set-range', (v) => { project.sprintRange = v; return { periodoTexto: v }; });
    wire('set-days', (v) => {
      const n = Math.max(0, parseInt(v, 10) || 0);
      project.daysRemaining = n;
      return { diasRestantes: n };
    });
  }

  /**
   * Volta a configuração ao padrão NO BANCO — ou seja, para todos.
   *
   * O aviso diz isso na cara: até aqui este botão limpava o `localStorage` e
   * afetava só quem clicou. Agora o mesmo clique tem alcance de instalação, e
   * quem aperta precisa saber disso ANTES.
   */
  async function resetAll() {
    const aviso =
      'Restaurar a configuração padrão?\n\n' +
      'Isto vale para TODOS os atendentes desta instalação, não só para você.';
    if (!window.confirm(aviso)) return;

    try {
      await PainelApi.salvarConfiguracao({
        nome: 'Chamados',
        sigla: 'CH',
        periodoRotulo: '',
        periodoTexto: '',
        diasRestantes: 0,
      });
      location.reload();
    } catch (err) {
      showToast('Não foi possível restaurar: ' + err.message);
    }
  }

  function openSettings() {
    settingsOpen = true;
    byId('set-name').value = project.name;
    byId('set-key').value = project.key;
    byId('set-sprint').value = project.sprint;
    byId('set-range').value = project.sprintRange;
    byId('set-days').value = project.daysRemaining;
    byId('settings-modal').classList.add('is-open');
    byId('settings-modal').setAttribute('aria-hidden', 'false');
    byId('settings-backdrop').classList.add('is-open');
  }

  function closeSettings() {
    settingsOpen = false;
    byId('settings-modal').classList.remove('is-open');
    byId('settings-modal').setAttribute('aria-hidden', 'true');
    byId('settings-backdrop').classList.remove('is-open');
  }

  function setupSettings() {
    bindSettingsFields();
    byId('settings-backdrop').addEventListener('click', closeSettings);
    byId('settings-close').addEventListener('click', closeSettings);
    byId('settings-done').addEventListener('click', closeSettings);
    byId('settings-reset').addEventListener('click', resetAll);
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && settingsOpen) closeSettings();
    });
  }

  /* ---------- Ajuda --------------------------------------------------- */

  let helpOpen = false;

  function openHelp() {
    helpOpen = true;
    byId('help-modal').classList.add('is-open');
    byId('help-modal').setAttribute('aria-hidden', 'false');
    byId('help-backdrop').classList.add('is-open');
  }

  function closeHelp() {
    helpOpen = false;
    byId('help-modal').classList.remove('is-open');
    byId('help-modal').setAttribute('aria-hidden', 'true');
    byId('help-backdrop').classList.remove('is-open');
  }

  function setupHelp() {
    byId('help-btn').addEventListener('click', openHelp);
    byId('help-backdrop').addEventListener('click', closeHelp);
    byId('help-close').addEventListener('click', closeHelp);
    byId('help-done').addEventListener('click', closeHelp);
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && helpOpen) closeHelp();
    });
  }

  /* ---------- Init ---------------------------------------------------- */

  function renderHeader() {
    byId('project-name').textContent = project.name;
    byId('project-initials').textContent = project.key.slice(0, 2);
    byId('breadcrumb-project').textContent = project.name;

    // Rótulo, período e dias restantes eram editáveis nas Configurações e não
    // apareciam em lugar NENHUM da tela - campo que se digita e evapora. Agora
    // saem aqui, e o chip só existe quando há o que mostrar: um chip vazio
    // ocupando espaço ao lado do título seria pior que nenhum.
    const chip = byId('periodo-chip');
    if (!chip) return;

    const partes = [];
    if (project.sprint) partes.push(project.sprint);
    if (project.sprintRange) partes.push(project.sprintRange);
    if (project.daysRemaining > 0) {
      partes.push(project.daysRemaining === 1 ? '1 dia restante' : project.daysRemaining + ' dias restantes');
    }

    chip.textContent = partes.join(' · ');
    chip.hidden = partes.length === 0;
  }

  async function init() {
    renderHeader();
    renderConta();

    setupToolbar();
    setupDragAndDrop();
    setupChrome();
    setupModal();
    setupPeople();
    setupSettings();
    setupHelp();
    setupTarefa();
    setupAssuntos();
    setupSetores();
    // `setupDashboard` no lugar do antigo `setupMetricas`: o resumo virou visão
    // de página, e a função do modal deixou de existir junto com ele.
    setupDashboard();
    setupConexao();

    render();
    renderConexao();

    // Sem token não adianta tentar: pede antes de bater na API e levar 401.
    if (PainelApi.temToken()) {
      // A árvore de assuntos vem ANTES dos chamados: o cartão guarda só o id, e
      // é ela que vira o rótulo. Invertido, a primeira renderização sairia com
      // os cartões sem assunto e piscaria ao corrigir.
      //
      // A configuração vem antes de tudo pelo mesmo motivo: é ela que dá nome
      // ao painel na barra lateral, e carregá-la depois deixaria o nome padrão
      // aparecer por um instante antes de ser corrigido.
      await carregarConfiguracao();
      await carregarAssuntos();
      await carregarSetores();
      await carregarPessoas();
      await carregarChamados();
    } else {
      abrirToken();
    }

    agendarAtualizacao();
  }

  document.addEventListener('DOMContentLoaded', init);
})();
