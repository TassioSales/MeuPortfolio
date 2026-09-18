import { criarApp } from './app';
import { config } from './config';
import { iniciarLimpezaDeSessoes } from './conversation/sessoes';
import { prepararBanco, prisma } from './db/client';
import { janelas, usandoRedis } from './estado/janelas';
import { erroSeguro, usarLogger } from './log';
import { iniciarVarredor } from './whatsapp/outbox';

const app = criarApp();

// A partir daqui, todo o código fora de rota (outbox, varredor, limpeza de
// sessões) escreve no mesmo logger das requisições, em vez de console.error.
usarLogger(app.log);

// Registrado no boot de propósito: com estado em memória e mais de uma
// instância, cada limite passa a valer POR PROCESSO e o efetivo vira
// INSTÂNCIAS x o configurado — sem nada quebrar e sem nada avisar. Uma linha no
// log de subida é o que transforma isso em algo que se percebe. Ver
// src/estado/janelas.ts.
app.log.info(
  usandoRedis
    ? 'Limites por telefone compartilhados no Redis (throttle e aviso de indisponibilidade)'
    : 'Limites por telefone em memória: corretos com UMA instância. Com mais de uma, defina REDIS_URL'
);

// Reenvia mensagens que ficaram pendentes na outbox.
iniciarVarredor();

// Descarta sessões abandonadas, que guardam dado pessoal (LGPD).
iniciarLimpezaDeSessoes();

// Encerramento limpo: para de aceitar conexões, deixa as requisições em voo
// terminarem e só então fecha o arquivo do banco.
let encerrando = false;
for (const sinal of ['SIGTERM', 'SIGINT'] as const) {
  process.on(sinal, async () => {
    if (encerrando) return;
    encerrando = true;
    app.log.info(`${sinal} recebido, encerrando...`);
    try {
      await app.close();
      await prisma.$disconnect();
      // Sem isto, uma conexão de Redis aberta segura o processo depois do
      // `app.close()` e o encerramento depende do SIGKILL do orquestrador.
      await janelas.encerrar();
      process.exit(0);
    } catch (err) {
      app.log.error(erroSeguro(err), 'Falha ao encerrar');
      process.exit(1);
    }
  });
}

// `prepararBanco` ANTES do listen, e não em paralelo: ele liga o WAL e confere
// que as chaves estrangeiras estão ativas. Atender a primeira mensagem com FK
// desligada não dá erro nenhum - só deixa o `ON DELETE CASCADE` do histórico de
// situação de fora, e o problema aparece meses depois, na retenção. Ver
// src/db/client.ts.
prepararBanco()
  .then(() => app.listen({ port: config.port, host: '0.0.0.0' }))
  .catch((err) => {
    app.log.error(erroSeguro(err), 'Não foi possível iniciar o servidor');
    process.exit(1);
  });
