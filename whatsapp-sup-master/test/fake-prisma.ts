import { Prisma } from '../src/generated/prisma/client';

/**
 * Prisma de mentira, em memória.
 *
 * Deixa o código real de handler/client/webhook/rotas rodar sem tocar em banco.
 * O que ele NÃO simula, e por isso não pode ser testado aqui:
 *   - a serialização de transações concorrentes (no SQLite ela vem do mutex do
 *     adaptador, não de uma instrução que dê para observar);
 *   - o índice único realmente rejeitando `whatsappMessageId` repetido
 *     (aqui a rejeição é imitada com um Set);
 *   - a SQL de reserva da outbox, cuja regra de elegibilidade é REIMPLEMENTADA
 *     em JS aqui embaixo - inclusive a comparação de data, que é justamente a
 *     parte que já quebrou duas vezes em SQL crua;
 *   - a FK de Mensagem -> Chamado impedindo apagar o chamado antes das
 *     mensagens (aqui nada reclama se a ordem for trocada);
 *   - o `onDelete: SetNull` de Categoria -> Chamado (aqui apagar uma categoria
 *     não zera a coluna de quem apontava para ela; a API recusa esse DELETE
 *     antes, e é isso que os testes cobrem).
 * Esses cinco precisam do arquivo de verdade: `npm run dev:verificar-banco`.
 */

export type Sessao = {
  telefone: string;
  etapa: string;
  editando: boolean;
  categoriaId: number | null;
  nome: string | null;
  resumo: string | null;
  descricao: string | null;
  criadoEm: Date;
  atualizadoEm: Date;
};

export type Categoria = {
  id: number;
  codigo: string;
  nome: string;
  rotulo: string;
  ordem: number;
  ativa: boolean;
  /** `false` = assunto de uso interno: fora do menu do WhatsApp, dentro do painel. */
  visivelNoWhatsapp: boolean;
  paiId: number | null;
};

export type Setor = {
  id: number;
  codigo: string;
  nome: string;
  ordem: number;
  ativo: boolean;
};

export type Pessoa = {
  id: number;
  nome: string;
  cor: string;
  /**
   * O `oid` do Entra ID de quem entrou, quando o perfil veio (ou foi adotado
   * por) um login. Opcional porque pessoa cadastrada à mão no painel nunca
   * teve login — e é justamente `oid: null` que a adoção procura.
   */
  oid?: string | null;
  email?: string | null;
};

export type Estado = {
  sessoes: Map<string, Sessao>;
  mensagens: any[];
  chamados: any[];
  mudancas: any[];
  categorias: Categoria[];
  setores: Setor[];
  /**
   * O cadastro de pessoas do painel. Entrou no dublê com o RESPONSAVEL do
   * chamado: `Chamado.responsavelId` aponta para ele, e a rota que grava a
   * classificacao confere se a pessoa existe antes de aceitar o id. Sem este
   * model, aquela checagem estourava com "Cannot read properties of undefined" e
   * o 400 esperado virava 500.
   */
  pessoas: Pessoa[];
  /**
   * As quatro tabelas que penduram de um chamado. Vivem soltas aqui, como as
   * outras, e a ligacao com o chamado e por `chamadoId` - menos as etiquetas,
   * que sao muitos-para-muitos e por isso moram como `tagIds` DENTRO da linha do
   * chamado (o dublê nao tem tabela de juncao).
   */
  tags: { id: number; nome: string }[];
  comentarios: any[];
  anexos: any[];
  dependencias: any[];
  wamids: Set<string>;
  updateManyArgs: any[];
  /**
   * Quantas transações foram abertas, quantas estiveram abertas ao mesmo tempo,
   * e quais escritas caíram dentro de alguma delas.
   */
  transacoes: { abertas: number; simultaneasMax: number; escritas: string[] };
  /** Telefones para os quais gravar mensagem deve estourar (injeção de falha). */
  falharPara: Set<string>;
  /** Faz `$queryRaw` estourar, para exercitar o /ready com banco fora. */
  bancoFora: boolean;
  prisma: any;
};

// `categoria` é a primeira etapa desde que o menu de assuntos entrou, e o padrão
// aqui precisa acompanhar o `@default(categoria)` do schema: uma sessão nova que
// nascesse em `nome` no dublê faria o teste do menu passar sem o menu existir.
const SESSAO_PADRAO = {
  etapa: 'categoria',
  editando: false,
  categoriaId: null,
  nome: null,
  resumo: null,
  descricao: null,
};

// Espera-base entre tentativas de envio; dobra a cada tentativa gasta. Precisa
// acompanhar BACKOFF_BASE_SEGUNDOS em src/whatsapp/outbox.ts.
const BACKOFF_BASE_MS = 30_000;

/**
 * Reimplementa em JS a regra da SQL de `reservarLote`: pendente, com payload,
 * abaixo do teto de tentativas e com a espera crescente já vencida.
 */
function reservarPendentes(e: Estado, maxTentativas: number, limite: number): any[] {
  const agora = Date.now();

  const elegiveis = e.mensagens
    .filter((m) => {
      if (m.remetente !== 'sistema' || m.enviadaEm || !m.payload) return false;
      const tentativas = m.tentativas ?? 0;
      if (tentativas >= maxTentativas) return false;
      const desde: Date = m.ultimaTentativaEm ?? m.timestamp;
      return agora - desde.getTime() >= BACKOFF_BASE_MS * 2 ** tentativas;
    })
    .sort((a, b) => a.timestamp.getTime() - b.timestamp.getTime())
    .slice(0, limite);

  for (const m of elegiveis) {
    m.tentativas = (m.tentativas ?? 0) + 1;
    m.ultimaTentativaEm = new Date(agora);
  }

  // As colunas aqui acompanham o RETURNING de `reservarLote`: `telefone` e
  // `texto` entraram para o varredor poder RECONSTRUIR um payload de formato
  // antigo (ver `corpoParaEnvio` em whatsapp/outbox.ts). Omiti-las aqui faria o
  // dublê exercitar uma reconstrução com `undefined` dos dois lados.
  return elegiveis.map((m) => ({
    id: m.id,
    payload: m.payload,
    tentativas: m.tentativas,
    telefone: m.telefone,
    texto: m.texto,
  }));
}

/**
 * Casa um registro contra o subconjunto de filtros do Prisma que este projeto
 * usa: igualdade, `lt`, `lte`, `gte`, `in`, `null`, `OR` e o filtro por relação
 * (`chamado: { dataAbertura: ... }`, que a contagem da retenção precisa).
 *
 * Filtro não simulado ESTOURA de propósito. Devolver `false` calado faria um
 * teste de retenção passar por não ter apagado nada - exatamente o resultado
 * que ele deveria acusar como erro.
 */
function casa(registro: any, where: any, e: Estado): boolean {
  if (!where) return true;

  return Object.entries<any>(where).every(([campo, cond]) => {
    if (campo === 'OR') return (cond as any[]).some((c) => casa(registro, c, e));

    // Filtro por relação: resolve o chamado pelo chamadoId e desce nele.
    if (campo === 'chamado') {
      const chamado = e.chamados.find((c) => c.id === registro.chamadoId);
      return chamado !== undefined && casa(chamado, cond, e);
    }

    const valor = registro[campo];
    if (cond === null) return valor === null || valor === undefined;

    if (cond && typeof cond === 'object' && !(cond instanceof Date)) {
      // Vários operadores no mesmo campo (`{ gte, lte }`, a janela das métricas)
      // precisam valer TODOS. Antes o primeiro `if` que casasse encerrava a
      // checagem, e uma janela com as duas pontas era aplicada só pela primeira.
      return Object.entries<any>(cond).every(([op, alvo]) => {
        if (op === 'lt') return valor != null && valor < alvo;
        if (op === 'lte') return valor != null && valor <= alvo;
        if (op === 'gte') return valor != null && valor >= alvo;
        if (op === 'in') return (alvo as any[]).includes(valor);
        throw new Error(`filtro não simulado neste dublê: ${campo}.${op}`);
      });
    }

    return valor === cond;
  });
}

/**
 * `orderBy` do Prisma, incluindo a forma em LISTA (`[{ ordem }, { id }]`).
 *
 * A lista importa: o menu de assuntos desempata `ordem` por `id` justamente
 * porque duas categorias podem ter a mesma posição, e sem o desempate a
 * numeração mudaria de uma mensagem para a outra. Ignorar o segundo critério
 * aqui faria esse teste passar por acaso, pela ordem de inserção.
 */
function ordenar<T extends Record<string, any>>(lista: T[], orderBy: any): T[] {
  if (!orderBy) return lista;
  const criterios: any[] = Array.isArray(orderBy) ? orderBy : [orderBy];

  return [...lista].sort((a, b) => {
    for (const criterio of criterios) {
      const [campo, direcao] = Object.entries<any>(criterio)[0];
      const va = a[campo];
      const vb = b[campo];
      if (va === vb) continue;
      if (va == null) return 1;
      if (vb == null) return -1;
      const cmp = va < vb ? -1 : 1;
      return direcao === 'desc' ? -cmp : cmp;
    }
    return 0;
  });
}

/**
 * Aplica o `select` do Prisma, inclusive `_count`.
 *
 * Devolver o registro inteiro quando a consulta pediu colunas específicas
 * esconde exatamente o erro que o `select` existe para evitar: o campo ausente
 * chega como `undefined` no dublê e como `null` no banco. Foi assim que
 * `telefone` ganhou o `?? null` explícito aqui - um guarda escrito como
 * `=== null` passava no teste e falhava em produção. Agora a regra é geral.
 */
/**
 * As relações que um `select` pode pedir aninhadas, por NOME DE CAMPO.
 *
 * Um mapa só para todos os modelos, e não um por modelo, porque os nomes já são
 * distintos entre si - `comentarios` só existe em chamado, `bloqueador` só em
 * dependência. Se um dia dois modelos tiverem um campo de relação com o mesmo
 * nome, este mapa precisa virar dois.
 *
 * Cada função devolve o valor JÁ PROJETADO pelo `select` de dentro: é o que
 * permite ao dublê responder à consulta única do `GET .../detalhe`, que desce
 * dois níveis (chamado -> dependência -> chamado).
 */
const RELACOES: Record<string, (registro: any, pedido: any, e: Estado) => any> = {
  // A conversa do WhatsApp. Filtra por `chamadoId` como as outras, e o dublê
  // guarda as mensagens numa lista só (`e.mensagens`), com o vínculo sendo a
  // coluna - igual ao banco.
  mensagens: (c, pedido, e) => {
    const minhas = e.mensagens.filter((m) => m.chamadoId === c.id);
    return ordenar(minhas, pedido.orderBy).map((m) => projetar(m, pedido.select, e));
  },
  tags: (c, pedido, e) => {
    const minhas = e.tags.filter((t) => (c.tagIds ?? []).includes(t.id));
    return ordenar(minhas, pedido.orderBy).map((t) => projetar(t, pedido.select, e));
  },
  comentarios: (c, pedido, e) => {
    const meus = e.comentarios.filter((x) => x.chamadoId === c.id);
    return ordenar(meus, pedido.orderBy).map((x) => projetar(x, pedido.select, e));
  },
  anexos: (c, pedido, e) => {
    const meus = e.anexos.filter((x) => x.chamadoId === c.id);
    return ordenar(meus, pedido.orderBy).map((x) => projetar(x, pedido.select, e));
  },
  bloqueadoPor: (c, pedido, e) => {
    const minhas = e.dependencias.filter((d) => d.bloqueadoId === c.id);
    return ordenar(minhas, pedido.orderBy).map((d) => projetar(d, pedido.select, e));
  },
  bloqueia: (c, pedido, e) => {
    const minhas = e.dependencias.filter((d) => d.bloqueadorId === c.id);
    return ordenar(minhas, pedido.orderBy).map((d) => projetar(d, pedido.select, e));
  },
  bloqueador: (d, pedido, e) => {
    const c = e.chamados.find((x) => x.id === d.bloqueadorId);
    return c ? projetar(c, pedido.select, e) : null;
  },
  bloqueado: (d, pedido, e) => {
    const c = e.chamados.find((x) => x.id === d.bloqueadoId);
    return c ? projetar(c, pedido.select, e) : null;
  },
};

/**
 * `_count` depende de QUAL modelo está sendo projetado, porque a relação
 * `chamados` existe nos dois: em `Categoria` ela é `categoriaId`, em `Setor` é
 * `setorId`. Sem o parâmetro, contar os chamados de um setor devolveria os de
 * uma categoria de mesmo id - um número plausível e errado, que é o pior tipo.
 */
type Modelo = 'categoria' | 'setor';

function contar(relacao: string, registro: any, e: Estado, modelo: Modelo): number {
  if (modelo === 'setor') {
    if (relacao === 'chamados') return e.chamados.filter((c) => c.setorId === registro.id).length;
    if (relacao === 'origens') {
      return e.chamados.filter((c) => c.setorOrigemId === registro.id).length;
    }
    throw new Error(`relação não simulada em _count de setor: ${relacao}`);
  }

  if (relacao === 'chamados') return e.chamados.filter((c) => c.categoriaId === registro.id).length;
  if (relacao === 'filhas') return e.categorias.filter((c) => c.paiId === registro.id).length;
  throw new Error(`relação não simulada em _count: ${relacao}`);
}

function projetar(registro: any, select: any, e: Estado, modelo: Modelo = 'categoria'): any {
  if (!select) return { ...registro };

  const saida: any = {};
  for (const [campo, pedido] of Object.entries<any>(select)) {
    if (!pedido) continue;

    if (campo === '_count') {
      const contagem: any = {};
      for (const relacao of Object.keys(pedido.select ?? {})) {
        contagem[relacao] = contar(relacao, registro, e, modelo);
      }
      saida._count = contagem;
      continue;
    }

    const relacao = RELACOES[campo];
    if (relacao && typeof pedido === 'object') {
      saida[campo] = relacao(registro, pedido, e);
      continue;
    }

    saida[campo] = registro[campo] ?? null;
  }
  return saida;
}

function erroDeUnicidade(alvo: string[]): Prisma.PrismaClientKnownRequestError {
  return new Prisma.PrismaClientKnownRequestError('Unique constraint failed', {
    code: 'P2002',
    clientVersion: '7.9.1',
    meta: { target: alvo },
  });
}

/**
 * Preenche uma categoria de teste. Só `codigo`/`rotulo` costumam importar para o
 * que está sendo verificado; o resto tem padrão para o teste não virar formulário.
 */
function completarCategoria(parcial: Partial<Categoria>, indice: number): Categoria {
  const codigo = parcial.codigo ?? `assunto_${indice + 1}`;
  return {
    id: parcial.id ?? indice + 1,
    codigo,
    nome: parcial.nome ?? codigo.toUpperCase(),
    rotulo: parcial.rotulo ?? parcial.nome ?? codigo.toUpperCase(),
    ordem: parcial.ordem ?? indice + 1,
    ativa: parcial.ativa ?? true,
    visivelNoWhatsapp: parcial.visivelNoWhatsapp ?? true,
    paiId: parcial.paiId ?? null,
  };
}

/** Mesmo espírito de `completarCategoria`: padrão para o teste não virar formulário. */
function completarSetor(parcial: Partial<Setor>, indice: number): Setor {
  const codigo = parcial.codigo ?? `setor_${indice + 1}`;
  return {
    id: parcial.id ?? indice + 1,
    codigo,
    nome: parcial.nome ?? codigo.toUpperCase(),
    ordem: parcial.ordem ?? indice + 1,
    ativo: parcial.ativo ?? true,
  };
}

/**
 * O muitos-para-muitos de etiquetas, do jeito que as rotas o escrevem:
 * `{ set: [] }` limpa e `{ connectOrCreate: [...] }` liga, criando a `Tag` que
 * ainda não existe.
 *
 * A ordem entre os dois importa e é a que o Prisma usa: `set` primeiro. Invertida,
 * o `PUT /tags` apagaria as etiquetas que acabou de conectar.
 */
function aplicarTags(chamado: any, spec: any, e: Estado): void {
  if (!spec) return;
  if (!Array.isArray(chamado.tagIds)) chamado.tagIds = [];

  if (spec.set !== undefined) {
    if (spec.set.length > 0) throw new Error('`set` com ids não é simulado neste dublê');
    chamado.tagIds = [];
  }

  for (const item of spec.connectOrCreate ?? []) {
    const nome = item.where.nome;
    let tag = e.tags.find((t) => t.nome === nome);
    if (!tag) {
      tag = { id: e.tags.length + 1, nome };
      e.tags.push(tag);
    }
    if (!chamado.tagIds.includes(tag.id)) chamado.tagIds.push(tag.id);
  }
}

export function criarFakePrisma(
  sessaoInicial?: Partial<Sessao> & { telefone: string },
  categoriasIniciais: Partial<Categoria>[] = [],
  setoresIniciais: Partial<Setor>[] = [],
  pessoasIniciais: Partial<Pessoa>[] = []
): Estado {
  const e: Estado = {
    sessoes: new Map(),
    mensagens: [],
    chamados: [],
    mudancas: [],
    categorias: categoriasIniciais.map(completarCategoria),
    setores: setoresIniciais.map(completarSetor),
    pessoas: pessoasIniciais.map((x, i) => ({
      id: x.id ?? i + 1,
      nome: x.nome ?? `Pessoa ${i + 1}`,
      cor: x.cor ?? '#0052CC',
      // Sem padrão: pessoa semeada é pessoa cadastrada à mão, e o que a rota de
      // identidade decide depende exatamente de `oid` estar vazio ou não.
      oid: x.oid ?? null,
      email: x.email ?? null,
    })),
    tags: [],
    comentarios: [],
    anexos: [],
    dependencias: [],
    wamids: new Set(),
    updateManyArgs: [],
    transacoes: { abertas: 0, simultaneasMax: 0, escritas: [] },
    falharPara: new Set(),
    bancoFora: false,
    prisma: null,
  };

  if (sessaoInicial) {
    e.sessoes.set(sessaoInicial.telefone, {
      ...SESSAO_PADRAO,
      criadoEm: new Date('2026-01-01'),
      atualizadoEm: new Date(),
      ...sessaoInicial,
    } as Sessao);
  }

  // Quantas transações estão abertas AGORA. Fica fora de `models` porque as duas
  // pontas precisam dele: o `$transaction` para contar, e cada escrita para
  // registrar se aconteceu dentro ou fora.
  let abertas = 0;
  const registrar = (operacao: string) => {
    if (abertas > 0) e.transacoes.escritas.push(operacao);
  };

  const models = {
    $queryRaw: async (strings: TemplateStringsArray, ...vals: unknown[]) => {
      if (e.bancoFora) throw new Error('banco fora');
      const sql = strings.join(' ? ');

      if (/SELECT 1/i.test(sql)) return [{ um: 1 }];

      if (/UPDATE "Mensagem"/.test(sql)) {
        // Ordem dos parâmetros na SQL de reserva (whatsapp/outbox.ts):
        // 0 = a data do `ultimaTentativaEm`, 1 = teto de tentativas,
        // 2 = base do backoff em segundos, 3 = LIMIT.
        //
        // POSIÇÃO, e não nome: mexer na ordem dos `${}` daquela SQL sem mexer
        // aqui faz o dublê ler o limite no lugar do teto e vice-versa, e os
        // testes de outbox passam a medir outra coisa em silêncio. Foi o que
        // aconteceu quando a data entrou como primeiro parâmetro, na troca do
        // Postgres pelo SQLite.
        return reservarPendentes(e, Number(vals[1]), Number(vals[3]));
      }

      throw new Error(`$queryRaw não simulado neste dublê: ${sql}`);
    },
    mensagem: {
      create: async ({ data }: any) => {
        if (e.falharPara.has(data.telefone)) {
          throw new Error(`falha injetada para ${data.telefone}`);
        }
        if (data.whatsappMessageId) {
          if (e.wamids.has(data.whatsappMessageId)) {
            throw erroDeUnicidade(['whatsappMessageId']);
          }
          e.wamids.add(data.whatsappMessageId);
        }
        const m = { id: e.mensagens.length + 1, timestamp: new Date(), tentativas: 0, ...data };
        e.mensagens.push(m);
        registrar(`mensagem.create:${data.remetente}`);
        return m;
      },
      update: async ({ where, data }: any) => {
        const m = e.mensagens.find((x) => x.id === where.id);
        if (!m) throw new Error(`mensagem ${where.id} não existe`);
        for (const [k, v] of Object.entries<any>(data)) {
          m[k] = v && typeof v === 'object' && 'increment' in v ? (m[k] ?? 0) + v.increment : v;
        }
        return { ...m };
      },
      updateMany: async (args: any) => {
        e.updateManyArgs.push(args);
        return { count: 0 };
      },
      findMany: async ({ where, take }: any = {}) => {
        const achados = e.mensagens.filter((m) => casa(m, where, e));
        return (take ? achados.slice(0, take) : achados).map((m) => ({ ...m }));
      },
      deleteMany: async ({ where }: any = {}) => {
        const antes = e.mensagens.length;
        e.mensagens = e.mensagens.filter((m) => !casa(m, where, e));
        return { count: antes - e.mensagens.length };
      },
      count: async ({ where }: any = {}) => e.mensagens.filter((m) => casa(m, where, e)).length,
    },
    sessaoConversa: {
      findUnique: async ({ where }: any) => {
        const s = e.sessoes.get(where.telefone);
        return s ? { ...s } : null;
      },
      create: async ({ data }: any) => {
        const s = {
          ...SESSAO_PADRAO,
          criadoEm: new Date(),
          atualizadoEm: new Date(),
          ...data,
        } as Sessao;
        e.sessoes.set(data.telefone, s);
        registrar('sessaoConversa.create');
        return { ...s };
      },
      update: async ({ where, data }: any) => {
        const s = { ...e.sessoes.get(where.telefone)!, ...data };
        e.sessoes.set(where.telefone, s);
        registrar('sessaoConversa.update');
        return { ...s };
      },
      delete: async ({ where }: any) => {
        const s = e.sessoes.get(where.telefone);
        e.sessoes.delete(where.telefone);
        registrar('sessaoConversa.delete');
        return s;
      },
      deleteMany: async ({ where }: any) => {
        const corte = where?.atualizadoEm?.lt;
        if (corte) {
          let count = 0;
          for (const [telefone, s] of [...e.sessoes]) {
            if (s.atualizadoEm < corte) {
              e.sessoes.delete(telefone);
              count++;
            }
          }
          return { count };
        }
        const existia = e.sessoes.delete(where.telefone);
        return { count: existia ? 1 : 0 };
      },
      count: async ({ where }: any = {}) => {
        const corte = where?.atualizadoEm?.lt;
        if (corte) return [...e.sessoes.values()].filter((s) => s.atualizadoEm < corte).length;
        if (where?.telefone) return e.sessoes.has(where.telefone) ? 1 : 0;
        return e.sessoes.size;
      },
    },
    categoria: {
      findMany: async ({ where, orderBy, select }: any = {}) => {
        const achadas = ordenar(
          e.categorias.filter((c) => casa(c, where, e)),
          orderBy
        );
        return achadas.map((c) => projetar(c, select, e));
      },
      findFirst: async ({ where, orderBy, select }: any = {}) => {
        const achadas = ordenar(
          e.categorias.filter((c) => casa(c, where, e)),
          orderBy
        );
        return achadas.length > 0 ? projetar(achadas[0], select, e) : null;
      },
      findUnique: async ({ where, select }: any) => {
        const c = e.categorias.find((x) => x.id === where.id || x.codigo === where.codigo);
        return c ? projetar(c, select, e) : null;
      },
      create: async ({ data, select }: any) => {
        if (e.categorias.some((c) => c.codigo === data.codigo)) {
          throw erroDeUnicidade(['codigo']);
        }
        const proximoId = e.categorias.reduce((max, c) => Math.max(max, c.id), 0) + 1;
        const c: Categoria = {
          id: proximoId,
          ordem: 0,
          ativa: true,
          visivelNoWhatsapp: true,
          paiId: null,
          ...data,
        };
        e.categorias.push(c);
        registrar('categoria.create');
        return projetar(c, select, e);
      },
      update: async ({ where, data, select }: any) => {
        const c = e.categorias.find((x) => x.id === where.id);
        if (!c) throw new Error(`categoria ${where.id} não existe`);
        for (const [campo, valor] of Object.entries<any>(data)) {
          // `pai: { connect }` / `pai: { disconnect }` é como o Prisma escreve a
          // troca de pai numa relação; o dublê traduz para a coluna.
          if (campo === 'pai') {
            (c as any).paiId = valor?.disconnect ? null : (valor?.connect?.id ?? null);
            continue;
          }
          (c as any)[campo] = valor;
        }
        registrar('categoria.update');
        return projetar(c, select, e);
      },
      delete: async ({ where }: any) => {
        const i = e.categorias.findIndex((c) => c.id === where.id);
        if (i === -1) throw new Error(`categoria ${where.id} não existe`);
        const [removida] = e.categorias.splice(i, 1);
        registrar('categoria.delete');
        return removida;
      },
      count: async ({ where }: any = {}) => e.categorias.filter((c) => casa(c, where, e)).length,
    },
    mudancaSituacao: {
      create: async ({ data }: any) => {
        const m = { id: e.mudancas.length + 1, criadoEm: new Date(), autor: null, ...data };
        e.mudancas.push(m);
        return { ...m };
      },
      findMany: async ({ where, orderBy }: any = {}) => {
        const achadas = e.mudancas.filter((m) => casa(m, where, e));
        // O histórico do chamado pede `desc`; a série do dashboard pede `asc`.
        // Ordenar aqui é o que faz um teste de ordem provar alguma coisa em vez
        // de depender da ordem de inserção — e o `asc` importa mais: a
        // reconstrução da linha do tempo lê as transições em sequência, e um
        // dublê que devolvesse fora de ordem esconderia a dependência.
        if (orderBy?.criadoEm === 'desc') {
          achadas.sort((a, b) => b.criadoEm.getTime() - a.criadoEm.getTime());
        } else if (orderBy?.criadoEm === 'asc') {
          achadas.sort((a, b) => a.criadoEm.getTime() - b.criadoEm.getTime());
        }
        return achadas.map((m) => ({ ...m }));
      },
      count: async ({ where }: any = {}) => e.mudancas.filter((m) => casa(m, where, e)).length,
    },
    chamado: {
      create: async ({ data, select }: any) => {
        // Os defaults do schema que o código a jusante realmente lê. Sem eles,
        // um chamado criado aqui chegaria nas métricas sem `dataAbertura` e a
        // conta de SLA estouraria em cima do dublê, não em cima da regra.
        //
        // Os booleanos da classificação (`afetaAtendimento`, `envolveCusto`,
        // `precisaAprovacao`) são NOT NULL com default no banco, e é por isso que
        // entram aqui com `false` e não ausentes: `projetar` devolve `?? null`
        // para campo que não existe no registro, e o serializador do Fastify
        // recusaria `null` num campo declarado `boolean` obrigatório - uma falha
        // que só apareceria na resposta, longe da causa.
        const { tags, ...resto } = data;
        const c = {
          id: 100 + e.chamados.length,
          dataAbertura: new Date(),
          atualizadoEm: new Date(),
          origem: 'whatsapp',
          categoriaId: null,
          primeiroAtendimentoEm: null,
          resolvidoEm: null,
          tipo: null,
          setorId: null,
          setorOrigemId: null,
          responsavelId: null,
          prioridade: 'media',
          canal: 'whatsapp',
          prazoEm: null,
          afetaAtendimento: false,
          envolveCusto: false,
          precisaAprovacao: false,
          avaliacaoNota: null,
          avaliacaoComentario: null,
          avaliadoEm: null,
          tagIds: [] as number[],
          ...resto,
        };
        e.chamados.push(c);
        aplicarTags(c, tags, e);
        return projetar(c, select, e);
      },
      findUnique: async ({ where, select }: any) => {
        const c = e.chamados.find((x) => x.id === where.id);
        if (!c) return null;
        // Sem `select`, as colunas nuláveis ainda precisam sair como NULL e não
        // como `undefined` - ver o comentário em `projetar`.
        return select
          ? projetar(c, select, e)
          : {
              ...c,
              telefone: c.telefone ?? null,
              categoriaId: c.categoriaId ?? null,
              primeiroAtendimentoEm: c.primeiroAtendimentoEm ?? null,
              resolvidoEm: c.resolvidoEm ?? null,
            };
      },
      findMany: async ({ where, take, orderBy, select }: any = {}) => {
        const achados = ordenar(
          e.chamados.filter((c) => casa(c, where, e)),
          orderBy
        );
        return (take ? achados.slice(0, take) : achados).map((c) => projetar(c, select, e));
      },
      deleteMany: async ({ where }: any = {}) => {
        const antes = e.chamados.length;
        const sobrando = e.chamados.filter((c) => !casa(c, where, e));
        // Imita o `ON DELETE CASCADE` de MudancaSituacao. Sem isto o dublê
        // deixaria o histórico órfão em silêncio, e o teste de retenção passaria
        // sem provar que ele sai junto com o chamado.
        const vivos = new Set(sobrando.map((c) => c.id));
        e.mudancas = e.mudancas.filter((m) => vivos.has(m.chamadoId));
        e.chamados = sobrando;
        return { count: antes - e.chamados.length };
      },
      count: async ({ where }: any = {}) => e.chamados.filter((c) => casa(c, where, e)).length,
      update: async ({ where, data, select }: any) => {
        const c = e.chamados.find((x) => x.id === where.id);
        if (!c) throw new Error(`chamado ${where.id} não existe`);
        const { tags, ...resto } = data;
        Object.assign(c, resto);
        aplicarTags(c, tags, e);
        return projetar(c, select, e);
      },
    },

    // --- Setores ---------------------------------------------------------
    //
    // `modelo: 'setor'` nas projeções: é o que faz `_count.chamados` contar por
    // `setorId` em vez de por `categoriaId`. Ver o comentário em `contar`.
    setor: {
      findMany: async ({ where, orderBy, select }: any = {}) => {
        const achados = ordenar(
          e.setores.filter((x) => casa(x, where, e)),
          orderBy
        );
        return achados.map((x) => projetar(x, select, e, 'setor'));
      },
      findFirst: async ({ where, orderBy, select }: any = {}) => {
        const achados = ordenar(
          e.setores.filter((x) => casa(x, where, e)),
          orderBy
        );
        return achados.length > 0 ? projetar(achados[0], select, e, 'setor') : null;
      },
      findUnique: async ({ where, select }: any) => {
        const x = e.setores.find((y) => y.id === where.id || y.codigo === where.codigo);
        return x ? projetar(x, select, e, 'setor') : null;
      },
      create: async ({ data, select }: any) => {
        if (e.setores.some((x) => x.codigo === data.codigo)) throw erroDeUnicidade(['codigo']);
        const proximoId = e.setores.reduce((max, x) => Math.max(max, x.id), 0) + 1;
        const x: Setor = { id: proximoId, ordem: 0, ativo: true, ...data };
        e.setores.push(x);
        registrar('setor.create');
        return projetar(x, select, e, 'setor');
      },
      update: async ({ where, data, select }: any) => {
        const x = e.setores.find((y) => y.id === where.id);
        if (!x) throw new Error(`setor ${where.id} não existe`);
        Object.assign(x, data);
        registrar('setor.update');
        return projetar(x, select, e, 'setor');
      },
      delete: async ({ where }: any) => {
        const i = e.setores.findIndex((x) => x.id === where.id);
        if (i === -1) throw new Error(`setor ${where.id} não existe`);
        const [removido] = e.setores.splice(i, 1);
        registrar('setor.delete');
        return removido;
      },
      count: async ({ where }: any = {}) => e.setores.filter((x) => casa(x, where, e)).length,
    },

    // --- Comentários -----------------------------------------------------
    //
    // Só `create` e a leitura aninhada (que passa por `RELACOES`): não há rota
    // para editar nem para apagar comentário, de propósito - rastro que se
    // reescreve não é rastro. Um dublê com `update` aqui daria a impressão de que
    // existe.
    comentario: {
      create: async ({ data, select }: any) => {
        const x = { id: e.comentarios.length + 1, criadoEm: new Date(), autor: null, ...data };
        e.comentarios.push(x);
        registrar('comentario.create');
        return projetar(x, select, e);
      },
      count: async ({ where }: any = {}) => e.comentarios.filter((x) => casa(x, where, e)).length,
    },

    // --- Anexos ----------------------------------------------------------
    anexo: {
      findUnique: async ({ where, select }: any) => {
        const x = e.anexos.find((y) => y.id === where.id);
        return x ? projetar(x, select, e) : null;
      },
      create: async ({ data, select }: any) => {
        const x = { id: e.anexos.length + 1, criadoEm: new Date(), enviadoPor: null, ...data };
        e.anexos.push(x);
        registrar('anexo.create');
        return projetar(x, select, e);
      },
      delete: async ({ where }: any) => {
        const i = e.anexos.findIndex((x) => x.id === where.id);
        if (i === -1) throw new Error(`anexo ${where.id} não existe`);
        const [removido] = e.anexos.splice(i, 1);
        registrar('anexo.delete');
        return removido;
      },
      count: async ({ where }: any = {}) => e.anexos.filter((x) => casa(x, where, e)).length,
    },

    // --- Dependências ----------------------------------------------------
    //
    // `findUnique` aceita a chave COMPOSTA (`bloqueadoId_bloqueadorId`), que é
    // como as rotas checam o par: é ela que detecta a dependência repetida e a
    // inversa (o ciclo de dois).
    dependencia: {
      findUnique: async ({ where, select }: any) => {
        const par = where.bloqueadoId_bloqueadorId;
        const x = par
          ? e.dependencias.find(
              (y) => y.bloqueadoId === par.bloqueadoId && y.bloqueadorId === par.bloqueadorId
            )
          : e.dependencias.find((y) => y.id === where.id);
        return x ? projetar(x, select, e) : null;
      },
      create: async ({ data, select }: any) => {
        const repetida = e.dependencias.some(
          (y) => y.bloqueadoId === data.bloqueadoId && y.bloqueadorId === data.bloqueadorId
        );
        if (repetida) throw erroDeUnicidade(['bloqueadoId', 'bloqueadorId']);
        const x = { id: e.dependencias.length + 1, criadoEm: new Date(), ...data };
        e.dependencias.push(x);
        registrar('dependencia.create');
        return projetar(x, select, e);
      },
      delete: async ({ where }: any) => {
        const i = e.dependencias.findIndex((x) => x.id === where.id);
        if (i === -1) throw new Error(`dependencia ${where.id} não existe`);
        const [removida] = e.dependencias.splice(i, 1);
        registrar('dependencia.delete');
        return removida;
      },
      count: async ({ where }: any = {}) => e.dependencias.filter((x) => casa(x, where, e)).length,
    },

    // --- Pessoas ---------------------------------------------------------
    //
    // Cadastro de exibicao do painel, e desde a classificacao tambem o alvo de
    // `Chamado.responsavelId`. A rota de classificacao usa `findUnique` para
    // recusar um responsavel que nao existe com 400 em vez de deixar o Prisma
    // estourar P2003 e virar 500.
    pessoa: {
      findMany: async ({ where, orderBy, select }: any = {}) => {
        const achadas = ordenar(
          e.pessoas.filter((x) => casa(x, where, e)),
          orderBy
        );
        return achadas.map((x) => projetar(x, select, e));
      },
      /**
       * Duas chaves únicas, `id` e `oid` — as duas que o schema declara. Buscar
       * por `oid` é o que a rota de identidade faz para reencontrar quem já
       * entrou antes; se aqui só existisse `id`, aquela busca devolveria `null`
       * sempre e o dublê afirmaria que TODO login cria um perfil novo.
       *
       * Chave fora dessas duas estoura, como o resto deste arquivo: `null`
       * calado viraria "não achei" e o teste passaria pelo motivo errado.
       */
      findUnique: async ({ where, select }: any) => {
        let x: Pessoa | undefined;
        if (where.id !== undefined) x = e.pessoas.find((y) => y.id === where.id);
        else if (where.oid !== undefined)
          x = e.pessoas.find((y) => y.oid != null && y.oid === where.oid);
        else throw new Error(`pessoa.findUnique sem chave única simulada: ${Object.keys(where)}`);

        return x ? projetar(x, select, e) : null;
      },
      create: async ({ data, select }: any) => {
        const proximoId = e.pessoas.reduce((max, x) => Math.max(max, x.id), 0) + 1;
        const x: Pessoa = { id: proximoId, ...data };
        e.pessoas.push(x);
        registrar('pessoa.create');
        return projetar(x, select, e);
      },
      update: async ({ where, data, select }: any) => {
        const x = e.pessoas.find((y) => y.id === where.id);
        if (!x) throw new Error(`pessoa ${where.id} não existe`);
        Object.assign(x, data);
        registrar('pessoa.update');
        return projetar(x, select, e);
      },
      delete: async ({ where }: any) => {
        const i = e.pessoas.findIndex((x) => x.id === where.id);
        if (i === -1) throw new Error(`pessoa ${where.id} não existe`);
        const [removida] = e.pessoas.splice(i, 1);
        registrar('pessoa.delete');
        return removida;
      },
      count: async ({ where }: any = {}) => e.pessoas.filter((x) => casa(x, where, e)).length,
    },

    // --- Etiquetas -------------------------------------------------------
    //
    // A escrita de etiqueta acontece SEMPRE por `chamado.create`/`update` com
    // `connectOrCreate` (ver `aplicarTags`), então aqui só existe leitura.
    tag: {
      findMany: async ({ where, orderBy, select }: any = {}) => {
        const achadas = ordenar(
          e.tags.filter((t) => casa(t, where, e)),
          orderBy
        );
        return achadas.map((t) => projetar(t, select, e));
      },
      count: async ({ where }: any = {}) => e.tags.filter((t) => casa(t, where, e)).length,
    },
  };

  // O envio acontece depois do commit, usando o prisma de topo, então os mesmos
  // models precisam existir fora da transação.
  //
  // O contador de transações é o que sobrou de observável depois que o
  // `pg_advisory_xact_lock` saiu: no SQLite não há instrução de lock para
  // espionar, então o que os testes conferem é que a leitura e a escrita
  // acontecem DENTRO de uma transação - que é de onde vem a serialização.
  e.prisma = {
    $transaction: async (fn: any) => {
      abertas += 1;
      e.transacoes.abertas += 1;
      e.transacoes.simultaneasMax = Math.max(e.transacoes.simultaneasMax, abertas);
      try {
        return await fn(models);
      } finally {
        abertas -= 1;
      }
    },
    ...models,
  };
  return e;
}

export type RespostaProgramada =
  | {
      status: number;
      /** Valor do header `Retry-After` (segundos ou data HTTP), para o 429. */
      retryAfter?: string;
    }
  | 'erro-de-rede';

/**
 * Captura o que teria sido enviado à Graph API, sem rede.
 * `programar` define as respostas das próximas chamadas, para exercitar retry.
 */
export function capturarEnvios() {
  const enviados: any[] = [];
  const alertas: any[] = [];
  let programadas: RespostaProgramada[] = [];

  globalThis.fetch = (async (url: any, opts: any) => {
    // O alerta operacional (src/alerta.ts) também sai por `fetch`. Sem separar
    // pelo destino, todo teste que exercita uma desistência de envio veria o
    // alerta como se fosse mais uma mensagem para o usuário.
    if (String(url).includes('alerta.invalido')) {
      alertas.push(JSON.parse(opts.body));
      return { ok: true, status: 200, headers: new Headers(), text: async () => '' };
    }

    enviados.push(JSON.parse(opts.body));
    const proxima = programadas.shift();
    if (proxima === 'erro-de-rede') throw new Error('conexão recusada');
    const status = proxima?.status ?? 200;
    return {
      ok: status >= 200 && status < 300,
      status,
      // O código lê `Retry-After` daqui; sem um `headers` de verdade a leitura
      // estouraria em vez de simplesmente não achar o header.
      headers: new Headers(proxima?.retryAfter ? { 'retry-after': proxima.retryAfter } : {}),
      text: async () => 'erro simulado',
    };
  }) as any;

  return {
    enviados,
    alertas,
    // O corpo da Evolution tem um campo de texto e mais nada: `{ number, text }`.
    // Não há mais o ramo de mensagem interativa, porque menu virou texto
    // numerado — ver src/whatsapp/client.ts.
    ultimoTexto: () => {
      const u = enviados[enviados.length - 1];
      return u?.text ?? '';
    },
    /**
     * As opções do último menu, lidas de volta do TEXTO.
     *
     * Antes elas vinham estruturadas no corpo interativo, com id e título. Agora
     * o que trafega é texto numerado, então o id NÃO existe mais na mensagem: a
     * única coisa observável é a posição e o rótulo.
     *
     * Devolver a posição como `id` mantém os testes legíveis e reflete a
     * verdade nova — é o número que o usuário digita de volta.
     */
    ultimasOpcoes: (): { id: string; texto: string }[] => {
      const u = enviados[enviados.length - 1];
      const texto: string = u?.text ?? '';
      const opcoes: { id: string; texto: string }[] = [];
      for (const linha of texto.split('\n')) {
        const casou = /^(\d+)\.\s+(.*)$/.exec(linha.trim());
        if (casou) opcoes.push({ id: casou[1], texto: casou[2] });
      }
      return opcoes;
    },
    paraTelefone: (telefone: string) => enviados.filter((m) => m.number === telefone),
    programar: (lista: RespostaProgramada[]) => {
      programadas = [...lista];
    },
    reset: () => {
      enviados.length = 0;
      alertas.length = 0;
      programadas = [];
    },
  };
}
