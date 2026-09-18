import { FastifyInstance } from 'fastify';
import { prisma } from '../db/client';
import { exigirToken } from './auth';

/**
 * A configuração do painel: identidade (nome, sigla) e os rótulos do período.
 *
 * Existe pelo mesmo motivo de `pessoas.ts`: isso vivia no `localStorage` de cada
 * navegador. `Categoria`, `Setor` e `Pessoa` já tinham migrado para o banco, e
 * estes campos ficaram sendo os únicos ajustáveis na tela que NÃO eram
 * compartilhados — dois atendentes na mesma instalação viam nomes de projeto
 * diferentes, e não havia como saber qual era "o" nome.
 *
 * Linha única (`id = 1`), criada na primeira leitura. Não é tabela genérica de
 * chave/valor de propósito: com colunas nomeadas, `diasRestantes` é inteiro de
 * verdade e um relatório lê `periodoRotulo` sem parsear nada.
 *
 * Houve aqui, brevemente, um campo `areas` com os rótulos da seção "Áreas" do
 * painel. Ele saiu junto com a seção: ÁREA e SETOR eram o mesmo conceito, e
 * `Setor` já é tabela, com FK nos chamados e filtro no quadro. A classificação
 * de quem atende é uma só — ver `setores.ts`.
 */

const LINHA = 1;

// Textos livres, e não listas fechadas: são rótulos que os dashboards futuros
// vão ler, e fechar o vocabulário agora seria decidir por eles.
const TEXTO = (max: number) => ({ type: 'string', minLength: 0, maxLength: max }) as const;

const CORPO = {
  type: 'object',
  properties: {
    nome: TEXTO(120),
    sigla: TEXTO(8),
    periodoRotulo: TEXTO(120),
    periodoTexto: TEXTO(120),
    diasRestantes: { type: 'integer', minimum: 0, maximum: 9999 },
  },
  additionalProperties: false,
} as const;

const RESPOSTA = {
  type: 'object',
  properties: {
    nome: { type: 'string' },
    sigla: { type: 'string' },
    periodoRotulo: { type: 'string' },
    periodoTexto: { type: 'string' },
    diasRestantes: { type: 'integer' },
  },
  required: ['nome', 'sigla', 'periodoRotulo', 'periodoTexto', 'diasRestantes'],
} as const;

type Guardada = {
  nome: string;
  sigla: string;
  periodoRotulo: string;
  periodoTexto: string;
  diasRestantes: number;
};

function publicar(c: Guardada) {
  return {
    nome: c.nome,
    sigla: c.sigla,
    periodoRotulo: c.periodoRotulo,
    periodoTexto: c.periodoTexto,
    diasRestantes: c.diasRestantes,
  };
}

/**
 * Devolve a linha, criando-a com os padrões na primeira vez.
 *
 * `upsert` e não `findUnique` + `create`: a primeira abertura do painel depois
 * de uma instalação nova dispara duas leituras quase simultâneas (a página e a
 * atualização automática), e com dois passos as duas tentariam criar a linha.
 */
async function obter(): Promise<Guardada> {
  return prisma.configuracaoPainel.upsert({
    where: { id: LINHA },
    update: {},
    create: { id: LINHA },
  });
}

export function registrarRotasDeConfiguracao(app: FastifyInstance): void {
  app.get(
    '/internal/configuracao',
    {
      onRequest: exigirToken('Acesso negado à configuração do painel'),
      schema: { response: { 200: RESPOSTA } },
    },
    async () => publicar(await obter())
  );

  /**
   * Só o que veio no corpo é gravado — campo ausente é "não mexa".
   *
   * O painel manda um campo por vez, conforme o atendente sai dele, então um
   * PATCH que sobrescrevesse o resto com o estado da tela transformaria duas
   * pessoas editando ao mesmo tempo em uma apagando o trabalho da outra.
   */
  app.patch<{
    Body: {
      nome?: string;
      sigla?: string;
      periodoRotulo?: string;
      periodoTexto?: string;
      diasRestantes?: number;
    };
  }>(
    '/internal/configuracao',
    {
      onRequest: exigirToken('Acesso negado à configuração do painel'),
      schema: { body: CORPO, response: { 200: RESPOSTA } },
    },
    async (req) => {
      const b = req.body;
      await obter();

      const dados: Record<string, string | number> = {};
      if (b.nome !== undefined) dados.nome = b.nome.trim();
      if (b.sigla !== undefined) dados.sigla = b.sigla.trim();
      if (b.periodoRotulo !== undefined) dados.periodoRotulo = b.periodoRotulo.trim();
      if (b.periodoTexto !== undefined) dados.periodoTexto = b.periodoTexto.trim();
      if (b.diasRestantes !== undefined) dados.diasRestantes = b.diasRestantes;

      const atualizada = await prisma.configuracaoPainel.update({
        where: { id: LINHA },
        data: dados,
      });

      req.log.info({ campos: Object.keys(dados) }, 'Configuração do painel alterada');
      return publicar(atualizada);
    }
  );
}
