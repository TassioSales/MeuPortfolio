// A ordem aqui e a do enum `Etapa` no schema.prisma são a mesma coisa dita duas
// vezes. `categoria` entra ANTES de `nome` porque é a primeira pergunta depois
// da saudação: saber o assunto é o que separa os dados por atendimento, e
// perguntar isso depois de o formulário inteiro já ter sido preenchido seria
// pedir para a pessoa lembrar o que ela veio fazer.
// O que chegou do usuário. Separar clique de digitação importa: os ids de botão
// são protocolo interno ("editar_descricao", "cat_7") e não podem ser forjados
// digitando o mesmo texto.
//
// Mora aqui, e não no handler, porque o menu de assuntos precisa do tipo para
// interpretar a escolha - e `categorias.ts` importar do `handler.ts`, que
// importa `categorias.ts`, seria um ciclo.
export type Entrada =
  | { tipo: 'texto'; valor: string }
  | { tipo: 'botao'; id: string }
  | { tipo: 'midia'; formato: string };

export type Etapa = 'categoria' | 'nome' | 'resumo' | 'descricao' | 'confirmacao';

// As etapas em que o usuário DIGITA um texto livre.
//
// `categoria` NÃO entra, e a exclusão é o que mantém `LIMITES`, `rotulos` e
// `primeiroCampoVazio` corretos sem nenhum caso especial: o que chega naquela
// etapa é a escolha de um nó da árvore, validada contra o menu que acabou de ser
// oferecido (ver conversation/categorias.ts), e não um valor que vai direto para
// uma coluna de texto.
export type Campo = 'nome' | 'resumo' | 'descricao';

export const CAMPOS: readonly Campo[] = ['nome', 'resumo', 'descricao'] as const;

// Whitelist de verdade: um `as Campo` não valida nada em runtime, então o nome
// do campo que vem do id do botão passa por aqui antes de virar uma etapa.
export function ehCampo(valor: string): valor is Campo {
  return (CAMPOS as readonly string[]).includes(valor);
}

export const perguntas: Record<Etapa, string> = {
  // Montada com a árvore de `Categoria`, que é dado do banco e muda no painel:
  // ver `acaoMenuCategoria` em handler.ts e `textoDoMenu` em categorias.ts.
  categoria: '',
  // Serve como primeira mensagem também: quando não há categoria ativa
  // cadastrada a etapa de assunto é pulada, e esta vira a saudação.
  nome: 'Para abrir seu chamado, qual é o seu nome?',
  resumo: 'Obrigado! Agora resuma seu problema em uma frase curta.',
  descricao: 'Entendido. Pode descrever o problema com mais detalhes?',
  confirmacao: '', // montada dinamicamente com os dados coletados
};

export const proximaEtapa: Record<Etapa, Etapa | null> = {
  categoria: 'nome',
  nome: 'resumo',
  resumo: 'descricao',
  descricao: 'confirmacao',
  confirmacao: null,
};

export const MIN_CARACTERES = 2;

// Limite por campo, com mensagem amigável. Diferente do corte duro em
// whatsapp/webhook.ts, que existe só para barrar payload forjado.
export const LIMITES: Record<Campo, number> = {
  nome: 120,
  resumo: 200,
  descricao: 2000,
};

export const rotulos: Record<Campo, string> = {
  nome: 'Nome',
  resumo: 'Resumo',
  descricao: 'Descrição',
};

// A palavra que o usuário lê no lugar de "categoria". O banco chama de
// `Categoria` porque é o que a tabela é; quem está no WhatsApp entende
// "assunto", e o menu da empresa é literalmente uma lista de assuntos.
export const ROTULO_CATEGORIA = 'Assunto';

// Teto do corpo de uma mensagem que o bot envia.
//
// Já valeu 1024, e o número vinha da Meta: era o limite do corpo de uma mensagem
// INTERATIVA, e estourá-lo fazia a API RECUSAR o envio — o usuário travava na
// etapa final sem receber nada. A Evolution manda texto puro, onde esse teto não
// existe.
//
// Por que não virou ilimitado: o resumo da confirmação embute a descrição, que
// pode ter 2000 caracteres, e o menu de assuntos cresce com o cadastro. Sem teto
// nenhum, um menu grande viraria uma parede de texto. 4096 é o mesmo número que
// `MAX_CARACTERES_MENSAGEM` aplica na entrada — simetria proposital, e folgado o
// bastante para o truncamento deixar de ser um risco silencioso de perder opção
// de menu (ver `textoDoMenu` em categorias.ts).
export const MAX_CORPO_MENSAGEM = 4096;
export const MAX_DESCRICAO_NO_RESUMO = 500;

export const mensagens = {
  soTexto:
    'Por enquanto só consigo ler mensagens de texto — ainda não consigo ouvir ' +
    'áudio nem abrir anexos. Pode escrever, por favor?',
  cancelado:
    'Tudo bem, cancelei essa abertura de chamado. Quando quiser tentar de novo, ' +
    'é só me mandar uma mensagem.',
  // "cancelar" sem nada em andamento: dizer "cancelei essa abertura de chamado"
  // para quem nunca começou uma dá a entender que algo foi perdido.
  nadaParaCancelar:
    'Não tem nenhuma abertura de chamado em andamento agora. Quando precisar de ' +
    'ajuda, é só me mandar uma mensagem.',
  expirada: 'Faz um tempo que a gente parou, então vou começar de novo.',
  curtaDemais: 'Por favor, envie uma resposta um pouco mais detalhada.',
  useOsBotoes: 'Por favor, use os botões para confirmar, editar ou cancelar.',
  opcaoDesconhecida: 'Não reconheci essa opção. Use os botões, por favor.',
  // Recusa da etapa de assunto. Diz o QUE fazer ("responda com o número") em vez
  // de só recusar: o menu vem logo abaixo na mesma mensagem, então a pessoa não
  // precisa rolar a conversa para achar as opções de novo.
  assuntoDesconhecido: 'Não reconheci essa opção.',
  // O assunto onde a conversa estava saiu do menu enquanto ela acontecia
  // (desativado ou marcado como de uso interno no painel). A resposta que chegou
  // NÃO é aproveitada: ela foi escrita olhando um menu que não vale mais, e
  // aceitá-la escolheria, em silêncio, um assunto que a pessoa não leu.
  assuntoSaiuDoMenu: 'Esse assunto deixou de estar disponível. Vamos recomeçar a escolha:',
} as const;

// Comandos que valem em qualquer etapa. Comparados por igualdade exata contra o
// texto normalizado, para não engolir uma descrição legítima como
// "cancelar meu pedido no site".
export const PALAVRAS_CANCELAR: ReadonlySet<string> = new Set([
  'cancelar',
  'cancela',
  'reiniciar',
  'recomecar',
  'sair',
  'parar',
]);

/**
 * Texto do usuário reduzido à forma que dá para comparar.
 *
 * Mora aqui, e não no handler, porque agora tem DOIS consumidores: o handler
 * (comandos como "cancelar" e "confirmar") e o menu de assuntos, que precisa
 * casar o que a pessoa digitou com o rótulo de uma categoria. Duas cópias desta
 * função é como uma delas para de remover acento e ninguém percebe.
 */
export function normalizar(texto: string): string {
  return (
    texto
      .trim()
      .toLowerCase()
      .normalize('NFD')
      // Faixa dos diacríticos combinantes: remove acentos ("não" -> "nao").
      // Escrita como escape de propósito - com os caracteres literais, qualquer
      // problema de encoding no arquivo desligava a remoção em silêncio.
      .replace(/[\u0300-\u036f]/g, '')
  );
}
