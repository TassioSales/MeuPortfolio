import { FastifyReply, FastifyRequest } from 'fastify';
import { config } from '../config';
import { comparacaoSegura } from '../whatsapp/signature';

/**
 * Aceita o token interno e, se estiver configurado, o do painel.
 *
 * São dois porque vivem em lugares com risco diferente: o interno fica em
 * servidor, o do painel fica no navegador de cada atendente. Ter os dois
 * permite revogar o do painel sem derrubar nenhuma outra integração. Sem
 * `PAINEL_TOKEN` definido, existe só o interno e nada muda.
 */
export function autorizado(req: FastifyRequest): boolean {
  const header = req.headers.authorization;
  if (typeof header !== 'string' || !header.startsWith('Bearer ')) return false;

  const enviado = header.slice('Bearer '.length);
  // Os dois lados são sempre comparados, sem `||` de curto-circuito, para o
  // tempo de resposta não contar quantos tokens existem.
  const bateInterno = comparacaoSegura(enviado, config.internalApiToken);
  const batePainel = config.painelToken !== '' && comparacaoSegura(enviado, config.painelToken);
  return bateInterno || batePainel;
}

/**
 * O guarda de todas as rotas internas, como hook de `onRequest`.
 *
 * `onRequest` e não `preHandler`: o ciclo do Fastify roda a validação de schema
 * DEPOIS do preHandler, então autenticar ali deixaria quem não tem token receber
 * 400 com o nome dos campos e a lista de valores aceitos antes de levar o 401.
 * Aqui a requisição sem token morre antes de o corpo sequer ser lido.
 *
 * Virou fábrica quando a sexta rota interna repetiu o mesmo bloco de cinco
 * linhas: o que muda de uma para a outra é só a frase do log.
 */
export function exigirToken(aviso: string) {
  return async (req: FastifyRequest, reply: FastifyReply): Promise<void> => {
    if (!autorizado(req)) {
      req.log.warn(aviso);
      await reply.status(401).send({ erro: 'não autorizado' });
    }
  };
}
