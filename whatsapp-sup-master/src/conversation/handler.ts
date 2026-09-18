import { Prisma, SessaoConversa } from '../generated/prisma/client';
import { prisma } from '../db/client';
import { CorpoWhatsApp, OpcoesEnvio, corpoEscolha, corpoTexto } from '../whatsapp/client';
import { despachar } from '../whatsapp/outbox';
import { log } from '../log';
import {
  CABECALHO_FILHAS,
  CABECALHO_RAIZ,
  caminhoDaCategoria,
  filhasNoMenu,
  interpretarEscolha,
  noAindaOferecivel,
  opcoesDoMenu,
  paiDe,
  textoDoMenu,
} from './categorias';
import { corteExpiracao } from './sessoes';
import {
  CAMPOS,
  Campo,
  Entrada,
  Etapa,
  LIMITES,
  MAX_CORPO_MENSAGEM,
  MAX_DESCRICAO_NO_RESUMO,
  MIN_CARACTERES,
  PALAVRAS_CANCELAR,
  ROTULO_CATEGORIA,
  ehCampo,
  mensagens,
  normalizar,
  perguntas,
  proximaEtapa,
  rotulos,
} from './flows';

// `Entrada` mora em flows.ts desde que o menu de assuntos passou a precisar dela
// (importar daqui criaria um ciclo). Continua sendo reexportada porque
// whatsapp/webhook.ts a consome deste módulo.
export type { Entrada };

// O que o bot vai responder. A decisão é calculada dentro da transação; o envio
// (que é rede, e pode demorar) acontece depois do commit, para não segurar lock
// de banco durante uma chamada HTTP.
type Acao =
  | { tipo: 'nada' }
  | { tipo: 'texto'; texto: string; chamadoId?: number }
  // `botoes` é a INTENÇÃO ("ofereça estas opções"), não o formato do envio: quem
  // decide entre botões e lista é `corpoEscolha`, pelo número de opções.
  | {
      tipo: 'botoes';
      texto: string;
      botoes: { id: string; texto: string }[];
      rotuloLista?: string;
    };

const NADA: Acao = { tipo: 'nada' };

function truncar(texto: string, limite: number): string {
  return texto.length <= limite ? texto : `${texto.slice(0, limite - 1)}…`;
}

async function montarResumoConfirmacao(
  tx: Prisma.TransactionClient,
  sessao: SessaoConversa
): Promise<string> {
  // O caminho na árvore, e não só o rótulo da folha: numa árvore com
  // sub-assuntos, "PDV" sozinho não diz de qual suporte se trata. Sai da linha
  // quando não há assunto - o que é legítimo se nenhuma categoria está ativa.
  const assunto = await caminhoDaCategoria(tx, sessao.categoriaId);

  const corpo =
    `Confirma a abertura do chamado?\n\n` +
    (assunto ? `*${ROTULO_CATEGORIA}:* ${assunto}\n` : '') +
    `*Nome:* ${sessao.nome}\n` +
    `*Resumo:* ${sessao.resumo}\n` +
    `*Descrição:* ${truncar(sessao.descricao ?? '', MAX_DESCRICAO_NO_RESUMO)}`;

  // Cinto e suspensório: mesmo com a descrição encurtada, garante que o corpo
  // nunca ultrapasse o teto de uma mensagem.
  return truncar(corpo, MAX_CORPO_MENSAGEM);
}

async function acaoConfirmacao(
  tx: Prisma.TransactionClient,
  sessao: SessaoConversa,
  prefixo = ''
): Promise<Acao> {
  const resumo = await montarResumoConfirmacao(tx, sessao);
  return {
    tipo: 'botoes',
    texto: prefixo ? truncar(`${prefixo}\n\n${resumo}`, MAX_CORPO_MENSAGEM) : resumo,
    botoes: await opcoesDaConfirmacao(tx),
  };
}

/**
 * O menu da confirmação, ACHATADO em um nível só.
 *
 * Antes eram dois: "Confirmar / Editar / Cancelar" e, ao escolher Editar, um
 * segundo menu com os campos. Isso funcionava porque cada botão carregava um id
 * (`editar` x `editar_nome`) e o id dizia de qual menu a resposta veio.
 *
 * Com texto numerado, o id se perde: a pessoa responde "2", e "2" seria "Editar"
 * no primeiro menu e "Corrigir o nome" no segundo — na MESMA etapa, porque a
 * sessão continua em `confirmacao` entre os dois. Não havia como desambiguar sem
 * guardar na sessão qual menu foi enviado por último, o que custaria uma coluna
 * e uma migração.
 *
 * Achatar resolve pelo desenho, e não por estado: existe um único menu possível
 * nesta etapa, então o número sempre quer dizer a mesma coisa. De quebra, corrigir
 * um campo passou a custar uma mensagem em vez de duas.
 *
 * A ORDEM É CONTRATO. Esta função é a única fonte da lista, usada tanto para
 * MONTAR o menu quanto para INTERPRETAR o número recebido — é o que garante que
 * as duas pontas não divirjam.
 */
async function opcoesDaConfirmacao(
  tx: Prisma.TransactionClient
): Promise<{ id: string; texto: string }[]> {
  const opcoes = [{ id: 'confirmar', texto: 'Confirmar e abrir o chamado' }];

  // "Corrigir: Descrição" e não "Corrigir a descrição": os rótulos vêm de
  // `flows.ts` e têm gêneros diferentes (o nome, o resumo, A descrição). Montar
  // a frase com artigo obrigaria a guardar o gênero de cada rótulo só para o
  // menu ficar certo — e um rótulo novo entraria errado por omissão.
  const raizes = await filhasNoMenu(tx, null);
  if (raizes.length > 0) {
    opcoes.push({ id: ID_EDITAR_CATEGORIA, texto: `Corrigir: ${ROTULO_CATEGORIA}` });
  }

  for (const campo of CAMPOS) {
    opcoes.push({ id: `editar_${campo}`, texto: `Corrigir: ${rotulos[campo]}` });
  }

  opcoes.push({ id: 'cancelar', texto: 'Cancelar' });
  return opcoes;
}

// --- Etapa de assunto (árvore de Categoria) ------------------------------

/**
 * Sai da etapa de assunto para a próxima coisa a perguntar.
 *
 * Dois destinos, e a diferença é o `editando`: quem chegou aqui corrigindo o
 * assunto volta direto para a confirmação (mesma regra de `decidirColeta`); quem
 * está abrindo o chamado segue para o nome.
 *
 * O assunto escolhido é repetido junto com a pergunta seguinte de propósito: a
 * escolha foi um número, e ver o rótulo por extenso é o que permite perceber na
 * hora que se digitou 4 em vez de 5.
 */
async function avancarDaCategoria(
  tx: Prisma.TransactionClient,
  telefone: string,
  sessao: SessaoConversa,
  prefixo = ''
): Promise<Acao> {
  if (sessao.editando) {
    const final = await tx.sessaoConversa.update({
      where: { telefone },
      data: { etapa: 'confirmacao', editando: false },
    });
    return acaoConfirmacao(tx, final, prefixo);
  }

  const proxima = proximaEtapa.categoria;
  if (proxima === null) return NADA; // inalcançável; existe para o tipo fechar

  await tx.sessaoConversa.update({ where: { telefone }, data: { etapa: proxima } });

  // O `prefixo` é o aviso que veio de fora ("só consigo ler texto", "vou começar
  // de novo") e PRECISA sobreviver a este desvio. Sem categoria ativa cadastrada
  // esta função vira o caminho da PRIMEIRA resposta de toda conversa - engolir o
  // prefixo aqui apagava o aviso justamente nos dois casos em que ele era a
  // mensagem inteira.
  const assunto = await caminhoDaCategoria(tx, sessao.categoriaId);
  const partes = [
    prefixo,
    assunto ? `*${ROTULO_CATEGORIA}:* ${assunto}` : '',
    perguntas[proxima],
  ].filter((parte) => parte !== '');

  return { tipo: 'texto', texto: partes.join('\n\n') };
}

/**
 * Devolve a sessão com o nó da árvore garantidamente válido, voltando à raiz
 * quando ele deixou de ser oferecível.
 *
 * O caso é o painel mexendo na árvore com uma conversa em andamento. Marcar um
 * assunto guarda-chuva como de uso interno (ou desativá-lo) tira ele do menu na
 * hora — mas quem JÁ DESCEU para dentro dele não passa mais por esse filtro:
 * `filhasNoMenu` olha as filhas, e as filhas continuam com a coluna delas
 * intacta. Sem este reset, elas seguiriam sendo oferecidas àquela pessoa até a
 * sessão expirar, horas depois. "Só uso interno" tem de valer para a conversa
 * que já estava aberta, e não só para a próxima.
 *
 * Voltar para a raiz, e não subir até o primeiro ancestral válido: o ramo em que
 * a pessoa estava saiu de circulação inteiro, e recomeçar do menu principal é o
 * único ponto sobre o qual não há dúvida. Ela perde a descida, e é o que se quer
 * — o assunto que ela estava refinando não é mais oferecido.
 *
 * Custa uma consulta por nível, e só quando há nó (na raiz, que é onde a maioria
 * das mensagens da etapa acontece, sai na primeira linha sem tocar no banco).
 */
async function comNoValido(
  tx: Prisma.TransactionClient,
  telefone: string,
  sessao: SessaoConversa
): Promise<SessaoConversa> {
  if (sessao.categoriaId === null) return sessao;
  if (await noAindaOferecivel(tx, sessao.categoriaId)) return sessao;

  log.info(
    { telefone, categoriaId: sessao.categoriaId },
    'O assunto onde a conversa estava saiu do menu; voltando para a raiz'
  );
  return tx.sessaoConversa.update({ where: { telefone }, data: { categoriaId: null } });
}

/**
 * Monta o menu do nível onde a conversa está.
 *
 * `sessao.categoriaId` aqui é ONDE A PESSOA ESTÁ na árvore - o nó cujas filhas
 * estão sendo oferecidas -, e não a escolha final. Ele só vira a escolha quando
 * a etapa avança (ver o comentário no model `SessaoConversa`).
 *
 * Nenhuma filha oferecível embaixo do nó atual tem dois significados, e os dois
 * seguem em frente em vez de deixar a pessoa olhando para um menu vazio:
 *   - com `categoriaId` preenchido: as filhas saíram do menu - desativadas, ou
 *     marcadas como de uso interno no painel. O nó virou folha, e o que já foi
 *     escolhido vale. É o caso do assunto guarda-chuva cujos sub-assuntos são
 *     todos internos: a conversa para no pai, que é o que o cliente sabe dizer.
 *   - com `categoriaId` nulo: não há nenhum assunto oferecível cadastrado. A
 *     etapa inteira é pulada e o chamado nasce sem assunto - que
 *     `Chamado.categoriaId` aceita de propósito.
 */
async function acaoMenuCategoria(
  tx: Prisma.TransactionClient,
  telefone: string,
  sessaoRecebida: SessaoConversa,
  prefixo = ''
): Promise<Acao> {
  const sessao = await comNoValido(tx, telefone, sessaoRecebida);

  const filhas = await filhasNoMenu(tx, sessao.categoriaId);
  if (filhas.length === 0) return avancarDaCategoria(tx, telefone, sessao, prefixo);

  const opcoes = opcoesDoMenu(filhas);
  const podeVoltar = sessao.categoriaId !== null;
  const cabecalho = sessao.categoriaId === null ? CABECALHO_RAIZ : CABECALHO_FILHAS;

  return {
    tipo: 'texto',
    // TEXTO, e não `botoes`: `textoDoMenu` JÁ monta a lista numerada e a
    // instrução de responder com o número — ele sempre fez isso, porque com a
    // Meta o rótulo da lista era cortado em 24 caracteres e o número no corpo
    // era o caminho confiável.
    //
    // Passar isto por `corpoEscolha` numeraria tudo de novo, e o menu sairia com
    // as opções duplicadas. Foi o que aconteceu na primeira versão desta
    // migração, e o teste de categorias pegou.
    texto: textoDoMenu(prefixo ? `${prefixo}\n\n${cabecalho}` : cabecalho, opcoes, podeVoltar),
  };
}

async function decidirCategoria(
  tx: Prisma.TransactionClient,
  telefone: string,
  sessaoRecebida: SessaoConversa,
  entrada: Entrada
): Promise<Acao> {
  // Antes de INTERPRETAR, e não só antes de exibir: a whitelist sai das filhas
  // do nó atual, e um nó que saiu do menu enquanto a pessoa digitava faria a
  // resposta ser casada contra opções que não deviam mais existir.
  const sessao = await comNoValido(tx, telefone, sessaoRecebida);

  // Voltou para a raiz: a resposta que chegou é DESCARTADA, e o menu novo vai
  // com o aviso. Interpretar aqui seria o pior dos dois mundos - a pessoa
  // digitou "1" lendo o menu das filhas, e "1" no menu raiz é outro assunto
  // inteiro. Ela abriria o chamado numa categoria que nunca leu.
  if (sessao.categoriaId !== sessaoRecebida.categoriaId) {
    return acaoMenuCategoria(tx, telefone, sessao, mensagens.assuntoSaiuDoMenu);
  }

  const filhas = await filhasNoMenu(tx, sessao.categoriaId);
  if (filhas.length === 0) return avancarDaCategoria(tx, telefone, sessao);

  const opcoes = opcoesDoMenu(filhas);
  const podeVoltar = sessao.categoriaId !== null;
  const escolha = interpretarEscolha(entrada, opcoes, podeVoltar);

  // Não reconheci: repete o MESMO menu com o aviso na frente. Só recusar deixaria
  // a pessoa rolando a conversa para achar as opções de novo.
  if (escolha === null) {
    return acaoMenuCategoria(tx, telefone, sessao, mensagens.assuntoDesconhecido);
  }

  if (escolha.tipo === 'voltar') {
    const acima = sessao.categoriaId === null ? null : await paiDe(tx, sessao.categoriaId);
    const subiu = await tx.sessaoConversa.update({
      where: { telefone },
      data: { categoriaId: acima },
    });
    return acaoMenuCategoria(tx, telefone, subiu);
  }

  const escolhida = await tx.sessaoConversa.update({
    where: { telefone },
    data: { categoriaId: escolha.id },
  });

  // Tem sub-assunto? Desce um nível. Não tem? É a folha, e a escolha está feita.
  const netas = await filhasNoMenu(tx, escolha.id);
  if (netas.length > 0) return acaoMenuCategoria(tx, telefone, escolhida);

  return avancarDaCategoria(tx, telefone, escolhida);
}

/** Repete a pergunta da etapa atual, opcionalmente com um aviso antes. */
async function promptAtual(
  tx: Prisma.TransactionClient,
  telefone: string,
  sessao: SessaoConversa,
  prefixo = ''
): Promise<Acao> {
  if (sessao.etapa === 'confirmacao') return acaoConfirmacao(tx, sessao, prefixo);
  if (sessao.etapa === 'categoria') return acaoMenuCategoria(tx, telefone, sessao, prefixo);

  const pergunta = perguntas[sessao.etapa as Campo];
  return { tipo: 'texto', texto: prefixo ? `${prefixo}\n\n${pergunta}` : pergunta };
}

const PALAVRAS_CONFIRMAR = new Set(['confirmar', 'confirmo', 'confirma', 'sim', 'ok']);
const PALAVRAS_EDITAR = new Set(['editar', 'corrigir', 'alterar', 'mudar', 'nao']);

/**
 * Interpreta texto digitado na etapa de confirmação.
 *
 * Aceita as PALAVRAS humanas ("confirmar", "sim") como atalho, porque os botões
 * interativos nem sempre renderizam em todo cliente e sem isso o usuário ficaria
 * preso. Nunca aceita id interno de botão: digitar "editar_descricao" não é
 * reconhecido como comando.
 */
function intencaoDeTexto(valor: string): 'confirmar' | 'editar' | null {
  const t = normalizar(valor);
  if (PALAVRAS_CONFIRMAR.has(t)) return 'confirmar';
  if (PALAVRAS_EDITAR.has(t)) return 'editar';
  return null;
}

/**
 * Traduz o número digitado para o id da opção.
 *
 * A posição é 1-based, como o menu mostra. Fora da faixa devolve `null`, e quem
 * chama trata como resposta não reconhecida — nunca como a primeira opção, que
 * seria confirmar o chamado por engano.
 *
 * `^\d+$` sobre o texto já aparado: "2" vale, "2 por favor" não. É a mesma
 * regra dos comandos globais, e pelo mesmo motivo — uma descrição que comece com
 * número não pode virar escolha de menu.
 */
function idDoNumero(valor: string, opcoes: { id: string }[]): string | null {
  const t = valor.trim();
  if (!/^\d+$/.test(t)) return null;

  const posicao = Number(t);
  if (!Number.isInteger(posicao) || posicao < 1 || posicao > opcoes.length) return null;

  return opcoes[posicao - 1].id;
}

function ehPedidoDeCancelamento(entrada: Entrada): boolean {
  if (entrada.tipo === 'botao') return entrada.id === 'cancelar';
  if (entrada.tipo === 'texto') return PALAVRAS_CANCELAR.has(normalizar(entrada.valor));
  return false;
}

function primeiroCampoVazio(sessao: SessaoConversa): Campo | null {
  for (const campo of CAMPOS) {
    const valor = sessao[campo];
    if (valor === null || valor.trim() === '') return campo;
  }
  return null;
}

// Mesmo corte usado pela varredura de sessões abandonadas, para o descarte
// preguiçoso (aqui) e o periódico (sessoes.ts) nunca discordarem.
function expirou(sessao: SessaoConversa, agora: Date): boolean {
  return sessao.atualizadoEm < corteExpiracao(agora);
}

// --- Etapa de confirmação ------------------------------------------------

// O assunto entra no menu de correção com id próprio, e não em `CAMPOS`: ele não
// é campo de texto, então não tem limite de tamanho nem pergunta fixa - o que
// vem depois de escolhê-lo é o menu da árvore, não um prompt.
const ID_EDITAR_CATEGORIA = 'editar_categoria';

async function decidirConfirmacao(
  tx: Prisma.TransactionClient,
  telefone: string,
  sessao: SessaoConversa,
  entrada: Entrada
): Promise<Acao> {
  // Três formas de responder, e a ordem importa.
  //
  // 1. Id de botão, para conversa que começou antes da migração e ainda tem um
  //    menu interativo antigo na tela.
  // 2. O NÚMERO da opção — o caminho principal agora.
  // 3. As palavras humanas ("sim", "cancelar"), que sempre valeram.
  //
  // O número é resolvido contra a MESMA lista que montou o menu, reconstruída
  // aqui. Se a lista mudasse entre o envio e a resposta — por exemplo, alguém
  // desativa a última categoria nesse intervalo —, o número passaria a apontar
  // para outra opção. O intervalo é de segundos e o efeito é escolher o campo
  // vizinho, não algo destrutivo: confirmar e cancelar são as pontas da lista, e
  // ganhar ou perder o item do assunto desloca só o meio.
  const opcoes = await opcoesDaConfirmacao(tx);

  const comando =
    entrada.tipo === 'botao'
      ? entrada.id
      : entrada.tipo === 'texto'
        ? (idDoNumero(entrada.valor, opcoes) ?? intencaoDeTexto(entrada.valor))
        : null;

  if (comando === 'confirmar') {
    // Em vez de `sessao.nome!` e deixar o banco estourar, checamos e voltamos a
    // perguntar o que faltou.
    const faltando = primeiroCampoVazio(sessao);
    if (faltando) {
      await tx.sessaoConversa.update({
        where: { telefone },
        data: { etapa: faltando, editando: true },
      });
      return {
        tipo: 'texto',
        texto: `Faltou preencher *${rotulos[faltando]}*.\n\n${perguntas[faltando]}`,
      };
    }

    const chamado = await tx.chamado.create({
      data: {
        nome: sessao.nome!,
        telefone,
        // A folha escolhida no menu. Nulo aqui é legítimo: significa que não
        // havia assunto ativo para oferecer, e não que a pessoa recusou escolher.
        categoriaId: sessao.categoriaId,
        resumo: sessao.resumo!,
        descricao: sessao.descricao!,
        situacao: 'aberto',
      },
    });

    // `timestamp >= criadoEm` limita o vínculo às mensagens DESTA conversa.
    // Sem isso, qualquer conversa abandonada meses atrás seria anexada ao
    // chamado novo.
    await tx.mensagem.updateMany({
      where: { telefone, chamadoId: null, timestamp: { gte: sessao.criadoEm } },
      data: { chamadoId: chamado.id },
    });

    await tx.sessaoConversa.delete({ where: { telefone } });

    return {
      tipo: 'texto',
      texto: `Chamado #${chamado.id} aberto com sucesso! Em breve alguém da equipe vai te atender.`,
      chamadoId: chamado.id,
    };
  }

  // "Editar" digitado por extenso não escolhe campo nenhum — no menu achatado
  // não existe mais essa opção intermediária. Vale como "mostre o menu de novo",
  // que é o que a pessoa quer ao escrever a palavra.
  if (comando === 'editar') {
    return acaoConfirmacao(tx, sessao, 'Escolha o que deseja corrigir.');
  }

  // O campo pode vir de um número (já traduzido para o id em `comando`) ou de um
  // clique num botão antigo.
  const idDeEdicao = typeof comando === 'string' && comando.startsWith('editar_') ? comando : null;
  // Escolha de campo. O id chega aqui já resolvido — do NÚMERO digitado ou de um
  // clique em botão antigo —, e é `comando` que carrega os dois.
  if (idDeEdicao !== null) {
    if (idDeEdicao === ID_EDITAR_CATEGORIA) {
      // `categoriaId` volta a null, e isso é obrigatório. Durante a etapa
      // `categoria` essa coluna é ONDE A PESSOA ESTÁ na árvore: deixá-la
      // apontando para a folha escolhida antes faria o menu oferecer as filhas
      // daquela folha - que não existem - e a correção terminaria sem nunca ter
      // mostrado opção nenhuma.
      const reiniciada = await tx.sessaoConversa.update({
        where: { telefone },
        data: { etapa: 'categoria', editando: true, categoriaId: null },
      });
      return acaoMenuCategoria(tx, telefone, reiniciada);
    }

    const campo = idDeEdicao.slice('editar_'.length);
    if (!ehCampo(campo)) {
      // Antes, um id desconhecido virava `etapa` e explodia no banco, deixando o
      // usuário sem resposta nenhuma.
      return { tipo: 'texto', texto: mensagens.opcaoDesconhecida };
    }

    await tx.sessaoConversa.update({
      where: { telefone },
      data: { etapa: campo, editando: true },
    });
    return { tipo: 'texto', texto: perguntas[campo] };
  }

  return { tipo: 'texto', texto: mensagens.useOsBotoes };
}

// --- Etapas de coleta ----------------------------------------------------

async function decidirColeta(
  tx: Prisma.TransactionClient,
  telefone: string,
  sessao: SessaoConversa,
  entrada: Entrada
): Promise<Acao> {
  const campoAtual = sessao.etapa as Campo;

  // Clique em botão antigo (o WhatsApp mantém os botões clicáveis no histórico).
  // Sem esse desvio, "editar_nome" seria salvo como se fosse o nome da pessoa.
  if (entrada.tipo !== 'texto') return promptAtual(tx, telefone, sessao);

  const valor = entrada.valor.trim();

  if (valor.length < MIN_CARACTERES) {
    return { tipo: 'texto', texto: mensagens.curtaDemais };
  }

  const limite = LIMITES[campoAtual];
  if (valor.length > limite) {
    return {
      tipo: 'texto',
      texto:
        `Ficou um pouco longo (${valor.length} caracteres). ` +
        `Por favor, envie *${rotulos[campoAtual]}* com até ${limite} caracteres.`,
    };
  }

  const atualizada = await tx.sessaoConversa.update({
    where: { telefone },
    data: { [campoAtual]: valor },
  });

  // Resposta veio de um fluxo de edição: volta direto para a confirmação.
  if (atualizada.editando) {
    const final = await tx.sessaoConversa.update({
      where: { telefone },
      data: { etapa: 'confirmacao', editando: false },
    });
    return acaoConfirmacao(tx, final);
  }

  const proxima = proximaEtapa[campoAtual];
  if (!proxima) return NADA;

  const final = await tx.sessaoConversa.update({
    where: { telefone },
    data: { etapa: proxima },
  });

  if (proxima === 'confirmacao') return acaoConfirmacao(tx, final);
  return { tipo: 'texto', texto: perguntas[proxima as Etapa] };
}

// --- Orquestração --------------------------------------------------------

/**
 * Só considera duplicata a violação de unicidade do `whatsappMessageId`.
 * Sem essa checagem, qualquer outro P2002 seria engolido como se fosse entrega
 * repetida e a mensagem sumiria sem deixar rastro no log.
 */
function ehDuplicataDeEntrega(err: unknown): boolean {
  if (!(err instanceof Prisma.PrismaClientKnownRequestError) || err.code !== 'P2002') return false;

  const alvo = (err.meta as { target?: unknown } | undefined)?.target;
  if (alvo === undefined) return true; // sem detalhe: assume o caso mais provável
  const texto = Array.isArray(alvo) ? alvo.join(',') : String(alvo);
  return texto.includes('whatsappMessageId');
}

function textoParaLog(entrada: Entrada): string {
  if (entrada.tipo === 'texto') return entrada.valor;
  if (entrada.tipo === 'botao') return entrada.id;
  return `[${entrada.formato} recebido - formato não suportado]`;
}

/**
 * De onde veio a sessão desta mensagem.
 *
 * `nova` e `reiniciada` são casos diferentes com a MESMA consequência - a
 * mensagem que chegou não é resposta a pergunta nenhuma -, mas o aviso ao
 * usuário é outro: quem está começando não precisa ouvir que a gente parou.
 */
type OrigemSessao = 'existente' | 'nova' | 'reiniciada';

/** Carrega a sessão, descartando-a se ficou parada além do TTL. */
async function carregarSessao(
  tx: Prisma.TransactionClient,
  telefone: string,
  agora: Date
): Promise<{ sessao: SessaoConversa; origem: OrigemSessao }> {
  const existente = await tx.sessaoConversa.findUnique({ where: { telefone } });

  if (existente && !expirou(existente, agora)) {
    // Toca a sessão para o TTL ser de inatividade, e não de idade absoluta -
    // caso contrário mensagens que não mudam estado (entrada inválida) não
    // contariam como atividade.
    const sessao = await tx.sessaoConversa.update({
      where: { telefone },
      data: { atualizadoEm: agora },
    });
    return { sessao, origem: 'existente' };
  }

  if (existente) await tx.sessaoConversa.delete({ where: { telefone } });

  // `categoria` é a primeira etapa desde que o menu de assuntos entrou. Quando
  // não há categoria ativa cadastrada, `acaoMenuCategoria` pula a etapa na
  // primeira resposta - a conversa não trava por falta de dado de configuração.
  const sessao = await tx.sessaoConversa.create({ data: { telefone, etapa: 'categoria' } });
  return { sessao, origem: existente !== null ? 'reiniciada' : 'nova' };
}

function acaoParaCorpo(telefone: string, acao: Acao): CorpoWhatsApp | null {
  if (acao.tipo === 'texto') return corpoTexto(telefone, acao.texto);
  if (acao.tipo === 'botoes')
    return corpoEscolha(telefone, acao.texto, acao.botoes, acao.rotuloLista);
  return null;
}

/** Roteia para a etapa certa e devolve o que responder. */
async function decidir(
  tx: Prisma.TransactionClient,
  telefone: string,
  entrada: Entrada
): Promise<Acao> {
  // Cancelar vale em qualquer etapa e não depende de a sessão existir.
  if (ehPedidoDeCancelamento(entrada)) {
    const { count } = await tx.sessaoConversa.deleteMany({ where: { telefone } });
    return { tipo: 'texto', texto: count > 0 ? mensagens.cancelado : mensagens.nadaParaCancelar };
  }

  const { sessao, origem } = await carregarSessao(tx, telefone, new Date());

  // Formato não suportado nunca avança o fluxo nem vira valor de campo:
  // explica a limitação e repete a pergunta da etapa atual.
  if (entrada.tipo === 'midia') return promptAtual(tx, telefone, sessao, mensagens.soTexto);

  // Primeiro contato: a mensagem que abre a conversa é saudação, não resposta.
  // Antes ela era gravada como NOME - quem escrevia "oi" ficava com nome="oi",
  // e todo o formulário deslizava um campo (o resumo virava o nome, e por aí).
  // A pergunta da primeira etapa só era alcançável por expiração, mídia ou
  // edição, ou seja: nunca no caminho que todo usuário novo percorre.
  if (origem === 'nova') return promptAtual(tx, telefone, sessao);

  if (origem === 'reiniciada') return promptAtual(tx, telefone, sessao, mensagens.expirada);

  if (sessao.etapa === 'confirmacao') return decidirConfirmacao(tx, telefone, sessao, entrada);
  if (sessao.etapa === 'categoria') return decidirCategoria(tx, telefone, sessao, entrada);
  return decidirColeta(tx, telefone, sessao, entrada);
}

/**
 * Grava a resposta na outbox, ainda dentro da transação do estado.
 *
 * Gravar aqui (e não depois do envio) é o que torna a entrega recuperável: se o
 * POST falhar, a linha fica pendente e o varredor reenvia. De quebra, o
 * histórico do chamado passa a registrar os dois lados mesmo quando a Evolution
 * está fora.
 */
async function enfileirarSaida(
  tx: Prisma.TransactionClient,
  telefone: string,
  acao: Acao
): Promise<{ id: number; corpo: CorpoWhatsApp } | null> {
  const corpo = acaoParaCorpo(telefone, acao);
  if (!corpo || acao.tipo === 'nada') return null;

  const linha = await tx.mensagem.create({
    data: {
      telefone,
      remetente: 'sistema',
      texto: acao.texto,
      chamadoId: acao.tipo === 'texto' ? (acao.chamadoId ?? null) : null,
      payload: corpo as Prisma.InputJsonValue,
      enviadaEm: null,
    },
  });

  return { id: linha.id, corpo };
}

/** `duplicata` = reentrega do webhook, já processada antes; nada foi alterado. */
export type ResultadoProcessamento = 'processada' | 'duplicata';

export async function processarMensagem(
  telefone: string,
  entrada: Entrada,
  whatsappMessageId?: string,
  opts: OpcoesEnvio = {}
): Promise<ResultadoProcessamento> {
  let saida: { id: number; corpo: CorpoWhatsApp } | null;

  try {
    saida = await prisma.$transaction(
      async (tx) => {
        // NÃO existe lock explícito aqui, e a ausência é deliberada.
        //
        // Duas mensagens do mesmo usuário chegando ao mesmo tempo liam a mesma
        // etapa e uma sobrescrevia a outra. No Postgres a correção era
        // `pg_advisory_xact_lock(hashtext(telefone))`: serializava só quem
        // disputava o MESMO telefone. No SQLite não há advisory lock, e também
        // não é preciso: o adaptador segura um mutex do `BEGIN` até o commit, e
        // com isso NENHUMA transação deste processo se sobrepõe a outra - o que
        // é mais forte do que serializar por telefone. Ver o comentário em
        // src/db/client.ts.
        //
        // A troca custa vazão: mensagens de telefones diferentes agora esperam
        // uma pela outra. Com o volume deste bot (dezenas de mensagens por
        // minuto, transação de milissegundos) isso não aparece; o que aparece
        // seria a corrida, se alguém "otimizasse" tirando a transação.

        // Idempotência: se este wamid já foi gravado, o índice único derruba a
        // transação inteira e a entrega repetida não avança o fluxo.
        await tx.mensagem.create({
          data: {
            telefone,
            remetente: 'usuario',
            texto: textoParaLog(entrada),
            whatsappMessageId: whatsappMessageId ?? null,
          },
        });

        const acao = await decidir(tx, telefone, entrada);
        return enfileirarSaida(tx, telefone, acao);
      },
      { maxWait: 5_000, timeout: 15_000 }
    );
  } catch (err) {
    // Entrega repetida do webhook: não avança o fluxo. Quem chamou precisa saber
    // para devolver a cota do telefone (ver whatsapp/webhook.ts).
    if (ehDuplicataDeEntrega(err)) return 'duplicata';
    throw err;
  }

  // Fora da transação: nenhuma chamada de rede segurando lock de banco.
  if (saida) await despachar(saida.id, saida.corpo, opts);
  return 'processada';
}
