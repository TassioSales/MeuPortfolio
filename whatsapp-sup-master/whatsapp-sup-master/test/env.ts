// Precisa ser o PRIMEIRO import de todo arquivo de teste: src/config.ts valida
// as variáveis no momento em que é carregado e mata o processo se faltar alguma.
Object.assign(process.env, {
  PORT: '3097',
  // O segredo que a Evolution apresenta no CAMINHO do webhook. Ver
  // src/whatsapp/signature.ts para por que ele substituiu a assinatura HMAC.
  WEBHOOK_SEGREDO: 'segredo_de_teste',
  // Host inventado de propósito: o dublê de fetch (`capturarEnvios`) separa o
  // que vai para cá do que vai para o alerta, e uma URL que não resolve garante
  // que um teste que escape do dublê falhe em vez de sair para a internet.
  EVOLUTION_URL: 'http://evolution.invalido',
  EVOLUTION_API_KEY: 'chave_falsa',
  EVOLUTION_INSTANCIA: 'suporte-teste',
  INTERNAL_API_TOKEN: 'token_interno_de_teste',
  // `:memory:` e não um caminho de arquivo: o dublê em memória (fake-prisma)
  // substitui o cliente antes de qualquer consulta, mas `src/db/client.ts` é
  // CARREGADO de qualquer forma - e é ele que resolve o caminho e cria o
  // diretório. Com um caminho de arquivo aqui, rodar os testes criaria um
  // `dados/` do lado do banco de verdade sem nenhum motivo.
  DATABASE_URL: 'file::memory:',
  // O dublê de fetch separa o que vai para este host do que vai para a Graph
  // (ver `capturarEnvios`), então ligar o alerta aqui não polui as asserções de
  // envio de mensagem.
  ALERTA_WEBHOOK_URL: 'http://alerta.invalido/teste',
  // Pequeno de proposito: e o que deixa o teste de anexo grande demais ser um
  // Buffer de 3 KB em vez de um corpo de varios megabytes por causa do default
  // de 5 MB. O limite em si e exercitado; so a escala e barata.
  ANEXO_MAX_BYTES: '3072',
});
