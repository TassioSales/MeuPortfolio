/**
 * Configuração do painel de chamados.
 *
 * Os cartões NÃO moram mais aqui: eles são os chamados do banco, lidos pela
 * API do bot de suporte (ver api.js). Este arquivo guarda só o endereço da API
 * e a forma do quadro.
 */

window.PAINEL_CONFIG = {
  /**
   * Vazio = MESMA ORIGEM do painel.
   *
   * Quem serve esta pasta é o `servidor-painel.mjs` (porta 8511), e ele repassa
   * `/internal/*` para o bot em 127.0.0.1:9511. Para o navegador, painel e API
   * estão no mesmo endereço — então não há CORS envolvido e o quadro funciona
   * igual aberto por localhost, pelo IP da máquina na rede ou por um domínio,
   * sem trocar nada aqui nem em `PAINEL_ORIGENS`.
   *
   * Só preencha se um dia o painel passar a falar com um bot em OUTRO host —
   * e, aí, essa origem precisa entrar em `PAINEL_ORIGENS` no .env do bot.
   *
   * Abrir o index.html direto do disco (file://) continua NÃO funcionando: a
   * origem vira "null" e o proxy não existe. Suba pelo `run.bat`.
   */
  apiBaseUrl: '',

  /** De quanto em quanto tempo recarregar os chamados. 0 desliga. */
  atualizarASegundos: 30,
};

window.BOARD_DATA = {
  project: {
    key: 'CH',
    name: 'Chamados',
    lead: 'Natan Ferreira',
    sprint: 'Suporte via WhatsApp',
    sprintRange: '—',
    daysRemaining: 0,
  },

  /**
   * Os ids das colunas são exatamente os valores do enum `Situacao` no banco.
   *
   * Isso é o que elimina a tabela de conversão: arrastar um cartão para a
   * coluna `resolvido` manda literalmente `situacao: "resolvido"` para a API.
   * Se um dia entrar uma situação nova no schema do Prisma, ela entra aqui com
   * o mesmo id e mais nada precisa mudar.
   */
  columns: [
    { id: 'aberto', name: 'A FAZER', limit: null },
    { id: 'em_andamento', name: 'EM ANDAMENTO', limit: null },
    // Entrou com a classificação. É o chamado parado esperando QUEM PEDIU, e não
    // por falta de atendimento — a coluna existe para que esse tempo não seja
    // lido como demora da equipe.
    { id: 'aguardando_resposta', name: 'AGUARDANDO RESPOSTA', limit: null },
    { id: 'resolvido', name: 'RESOLVIDO', limit: null },
    // Encerramento administrativo depois de resolvido (avaliado, contabilizado).
    // É a coluna onde a avaliação pós-fechamento faz sentido.
    { id: 'fechado', name: 'FECHADO', limit: null },
    { id: 'cancelado', name: 'CANCELADO', limit: null },
  ],

  /**
   * Chamado TEM responsável desde a classificação, e ele aponta para o cadastro
   * de pessoas — que vem do banco (`GET /internal/pessoas`), não daqui.
   *
   * A lista continua vazia neste arquivo de propósito: preenchê-la aqui seria
   * ressuscitar o cadastro local que já saiu do `localStorage` justamente para
   * ser compartilhado entre atendentes.
   */
  people: [],

  /**
   * As listas fixas dos campos de classificação, com o texto de tela.
   *
   * A CHAVE de cada item é literalmente o valor do enum no banco - é o que
   * elimina a tabela de conversão, do mesmo jeito que os ids das colunas são os
   * valores de `Situacao`. Trocar um rótulo aqui não mexe em dado nenhum;
   * acrescentar uma OPÇÃO exige migração, porque estes são enums do Prisma (ao
   * contrário de setor e assunto, que são tabela e mudam no painel).
   */
  listas: {
    tipo: [
      { id: 'interno', name: 'Interno' },
      { id: 'franquia', name: 'Franquia' },
    ],
    prioridade: [
      { id: 'baixa', name: 'Baixa' },
      { id: 'media', name: 'Média' },
      { id: 'alta', name: 'Alta' },
      { id: 'urgente', name: 'Urgente' },
    ],
    canal: [
      { id: 'whatsapp', name: 'WhatsApp' },
      { id: 'email', name: 'E-mail' },
      { id: 'telefone', name: 'Telefone' },
      { id: 'presencial', name: 'Presencial' },
    ],
    tipoSolicitacao: [
      { id: 'duvida', name: 'Dúvida' },
      { id: 'bug', name: 'Bug' },
      { id: 'melhoria', name: 'Melhoria' },
      { id: 'tarefa', name: 'Tarefa' },
      { id: 'projeto', name: 'Projeto' },
    ],
    impacto: [
      { id: 'sem_impacto', name: 'Sem impacto' },
      { id: 'baixo', name: 'Baixo' },
      { id: 'medio', name: 'Médio' },
      { id: 'alto', name: 'Alto' },
      { id: 'bloqueia_operacao', name: 'Bloqueia a operação' },
    ],
    tipoFranquia: [
      { id: 'financeiro', name: 'Financeiro' },
      { id: 'suprimentos', name: 'Suprimentos' },
      { id: 'sistema_pdv', name: 'Sistema / PDV' },
      { id: 'treinamento', name: 'Treinamento' },
      { id: 'manutencao_predial', name: 'Manutenção predial' },
      { id: 'marketing_local', name: 'Marketing local' },
      { id: 'juridico_contrato', name: 'Jurídico / contrato' },
    ],
    urgenciaComercial: [
      { id: 'rotina', name: 'Rotina' },
      { id: 'atencao', name: 'Atenção' },
      { id: 'loja_impactada', name: 'Loja impactada' },
      { id: 'loja_parada', name: 'Loja parada' },
    ],
  },

  // Preenchido pela API a cada carregamento.
  issues: [],
};
