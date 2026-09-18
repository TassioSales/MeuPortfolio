import { Prisma } from '../generated/prisma/client';
import { config } from '../config';
import {
  contarSessoesExpiradas,
  corteExpiracao,
  limparSessoesExpiradas,
} from '../conversation/sessoes';
import { prisma } from '../db/client';
import { ehTelefoneValido } from '../whatsapp/telefone';

/**
 * Retenção de dados pessoais (LGPD).
 *
 * Este script é o MECANISMO. A POLÍTICA — por quantos dias guardar mensagens e
 * chamados — é decisão do negócio e vem de `RETENCAO_MENSAGENS_DIAS` /
 * `RETENCAO_CHAMADOS_DIAS`. Sem essas variáveis nada disso é apagado, de
 * propósito: nenhum prazo é inventado aqui.
 *
 * Sessões abandonadas são a exceção e saem sempre: passado o `SESSAO_TTL_HORAS`
 * a sessão já seria descartada no próximo contato do usuário, então não há
 * decisão de negócio a tomar. Ver `conversation/sessoes.ts`.
 *
 * Por segurança, roda em modo simulação. Só apaga com `--confirmar`.
 *
 * Uso:
 *   npm run retencao                  # mostra o que seria apagado
 *   npm run retencao -- --confirmar   # apaga de verdade
 *   npm run retencao -- --esquecer 5511998877665 --confirmar   # pedido do titular
 */

// Apagar em lotes: depois de meses rodando sem política configurada, o primeiro
// `--confirmar` carregaria dezenas de milhares de ids de uma vez e montaria um
// `IN (...)` gigante numa única instrução.
export const TAMANHO_LOTE = 1_000;

function diasAtras(dias: number): Date {
  return new Date(Date.now() - dias * 24 * 60 * 60 * 1000);
}

type Cortes = { mensagens: Date | null; chamados: Date | null; sessoes: Date };

export function cortes(): Cortes {
  return {
    mensagens: config.retencaoMensagensDias ? diasAtras(config.retencaoMensagensDias) : null,
    chamados: config.retencaoChamadosDias ? diasAtras(config.retencaoChamadosDias) : null,
    sessoes: corteExpiracao(),
  };
}

export type Contagem = { mensagens: number; chamados: number; sessoes: number };

/**
 * O que a simulação mostra. Precisa bater com o que `aplicar()` apaga: num
 * comando destrutivo, a simulação É a trava de segurança, e uma trava que
 * mente para menos é pior que nenhuma.
 *
 * A contagem de mensagens tem duas origens, não uma: as velhas demais pelo
 * prazo de mensagens, MAIS as que estão penduradas em chamados que vão embora
 * (`apagarChamadosAntigos` leva as mensagens do chamado junto, a FK exige).
 * Contando só a primeira, um chamado de 60 dias com prazo de chamados em 30 e
 * prazo de mensagens em 90 fazia a simulação dizer "0 mensagens" e o
 * `--confirmar` apagar todas as mensagens dele.
 *
 * O `OR` é o que evita contar duas vezes a mensagem que se encaixa nos dois.
 */
export async function contar(): Promise<Contagem> {
  const c = cortes();

  const criterios: Prisma.MensagemWhereInput[] = [];
  if (c.mensagens) criterios.push({ timestamp: { lt: c.mensagens } });
  if (c.chamados) criterios.push({ chamado: { dataAbertura: { lt: c.chamados } } });

  return {
    mensagens: criterios.length ? await prisma.mensagem.count({ where: { OR: criterios } }) : 0,
    chamados: c.chamados
      ? await prisma.chamado.count({ where: { dataAbertura: { lt: c.chamados } } })
      : 0,
    sessoes: await contarSessoesExpiradas(),
  };
}

/** Apaga chamados antigos e, junto, as mensagens deles (a FK exige essa ordem). */
export async function apagarChamadosAntigos(
  corte: Date
): Promise<{ mensagens: number; chamados: number }> {
  let mensagens = 0;
  let chamados = 0;

  for (;;) {
    const alvos = await prisma.chamado.findMany({
      where: { dataAbertura: { lt: corte } },
      select: { id: true },
      take: TAMANHO_LOTE,
    });
    if (alvos.length === 0) break;

    const ids = alvos.map((c) => c.id);
    mensagens += (await prisma.mensagem.deleteMany({ where: { chamadoId: { in: ids } } })).count;
    chamados += (await prisma.chamado.deleteMany({ where: { id: { in: ids } } })).count;
  }

  return { mensagens, chamados };
}

export async function apagarMensagensAntigas(corte: Date): Promise<number> {
  let total = 0;

  for (;;) {
    const alvos = await prisma.mensagem.findMany({
      where: { timestamp: { lt: corte } },
      select: { id: true },
      take: TAMANHO_LOTE,
    });
    if (alvos.length === 0) break;

    total += (await prisma.mensagem.deleteMany({ where: { id: { in: alvos.map((m) => m.id) } } }))
      .count;
  }

  return total;
}

export async function aplicar(): Promise<Contagem> {
  const c = cortes();
  let mensagens = 0;
  let chamados = 0;

  if (c.chamados) {
    const r = await apagarChamadosAntigos(c.chamados);
    mensagens += r.mensagens;
    chamados += r.chamados;
  }

  if (c.mensagens) mensagens += await apagarMensagensAntigas(c.mensagens);

  return { mensagens, chamados, sessoes: await limparSessoesExpiradas() };
}

/** Direito à eliminação: apaga tudo que existe sobre um telefone. */
export async function esquecerTitular(telefone: string, confirmar: boolean): Promise<Contagem> {
  const chamados = await prisma.chamado.findMany({ where: { telefone }, select: { id: true } });
  const ids = chamados.map((c) => c.id);

  if (!confirmar) {
    return {
      mensagens: await prisma.mensagem.count({ where: { telefone } }),
      chamados: chamados.length,
      sessoes: await prisma.sessaoConversa.count({ where: { telefone } }),
    };
  }

  const mensagens =
    (await prisma.mensagem.deleteMany({ where: { telefone } })).count +
    (ids.length
      ? (await prisma.mensagem.deleteMany({ where: { chamadoId: { in: ids } } })).count
      : 0);
  const apagados = (await prisma.chamado.deleteMany({ where: { telefone } })).count;
  const sessoes = (await prisma.sessaoConversa.deleteMany({ where: { telefone } })).count;

  return { mensagens, chamados: apagados, sessoes };
}

export const SEM_POLITICA =
  'Atenção: RETENCAO_MENSAGENS_DIAS e RETENCAO_CHAMADOS_DIAS não estão definidos,\n' +
  'então mensagens e chamados NÃO são apagados. Esse prazo é uma decisão do\n' +
  'negócio; o script não assume nenhum valor. (Sessões abandonadas saem de todo\n' +
  'jeito: o prazo delas é o SESSAO_TTL_HORAS.)\n';

export type Argumentos = {
  confirmar: boolean;
  /** Presente quando veio `--esquecer`, mesmo que o telefone seja inválido. */
  esquecer: boolean;
  telefone: string | undefined;
};

/**
 * Lê a linha de comando. Separado do `main` porque é aqui que mora a decisão
 * mais perigosa do script - se `--confirmar` está ligado ou não - e isso
 * precisa ser verificável sem subir um processo.
 */
export function interpretarArgs(args: string[]): Argumentos {
  const iEsquecer = args.indexOf('--esquecer');
  return {
    confirmar: args.includes('--confirmar'),
    esquecer: iEsquecer >= 0,
    telefone: iEsquecer >= 0 ? args[iEsquecer + 1] : undefined,
  };
}

export async function main(args: string[] = process.argv.slice(2)): Promise<void> {
  const { confirmar, esquecer, telefone } = interpretarArgs(args);

  if (esquecer) {
    if (!ehTelefoneValido(telefone)) {
      console.error('Informe um telefone só com dígitos: --esquecer 5511998877665');
      process.exitCode = 1;
      return;
    }

    const r = await esquecerTitular(telefone, confirmar);
    console.log(
      confirmar
        ? `Apagado do titular ***${telefone.slice(-4)}: ${r.chamados} chamado(s), ` +
            `${r.mensagens} mensagem(ns), ${r.sessoes} sessão(ões).`
        : `[SIMULAÇÃO] Seriam apagados: ${r.chamados} chamado(s), ${r.mensagens} mensagem(ns), ` +
            `${r.sessoes} sessão(ões). Rode de novo com --confirmar.`
    );
    return;
  }

  const semPolitica = !config.retencaoMensagensDias && !config.retencaoChamadosDias;
  const c = cortes();

  if (!confirmar) {
    const n = await contar();
    console.log(
      `[SIMULAÇÃO] Seriam apagados ${n.mensagens} mensagem(ns), ${n.chamados} chamado(s) e ` +
        `${n.sessoes} sessão(ões) abandonada(s).\n` +
        `  corte de mensagens: ${c.mensagens?.toISOString() ?? '(desligado)'}\n` +
        `  corte de chamados:  ${c.chamados?.toISOString() ?? '(desligado)'}\n` +
        `  corte de sessões:   ${c.sessoes.toISOString()}\n` +
        (semPolitica ? SEM_POLITICA : '') +
        'Rode de novo com --confirmar para apagar.'
    );
    return;
  }

  const r = await aplicar();
  console.log(
    `Apagados ${r.mensagens} mensagem(ns), ${r.chamados} chamado(s) e ` +
      `${r.sessoes} sessão(ões) abandonada(s).` +
      (semPolitica ? `\n${SEM_POLITICA}` : '')
  );
}

// Só executa quando chamado direto (`npm run retencao`). Sem esta guarda,
// importar o módulo em um teste dispararia o script - com `--confirmar` vindo
// do argv de quem chamou.
if (require.main === module) {
  main()
    .catch((err) => {
      console.error('Falha na retenção:', err instanceof Error ? err.message : err);
      process.exitCode = 1;
    })
    .finally(() => prisma.$disconnect());
}
