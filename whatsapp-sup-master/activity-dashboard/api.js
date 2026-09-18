/**
 * Ponte entre o quadro e a API do bot de suporte (whatsapp-suporte).
 *
 * O quadro é uma página estática: não existe backend próprio aqui e o navegador
 * não fala com o banco. Quem lê o banco é o servidor do bot, que já o abre,
 * o token e os schemas. Este arquivo só sabe pedir e traduzir.
 *
 * Endereço e intervalo ficam em data.js (`window.PAINEL_CONFIG`).
 */
(function () {
  'use strict';

  // Chaves separadas de propósito. O token é credencial e sai quando a aba
  // fecha, a menos que a pessoa peça para lembrar; a preferência de aviso é
  // só conforto e pode ficar no navegador.
  const CHAVE_TOKEN = 'painel-chamados.token';
  const CHAVE_PREFS = 'painel-chamados.prefs';

  function lerPrefs() {
    try {
      return JSON.parse(localStorage.getItem(CHAVE_PREFS) || '{}');
    } catch (e) {
      return {};
    }
  }

  function gravarPrefs(prefs) {
    try {
      localStorage.setItem(CHAVE_PREFS, JSON.stringify(prefs));
    } catch (e) { /* modo privado ou cota cheia: segue sem lembrar */ }
  }

  const prefs = lerPrefs();

  /* ---------- Token ---------------------------------------------------- */

  function lerToken() {
    try {
      return sessionStorage.getItem(CHAVE_TOKEN) || localStorage.getItem(CHAVE_TOKEN) || '';
    } catch (e) {
      return '';
    }
  }

  /**
   * `lembrar` decide entre localStorage (sobrevive ao fechar o navegador) e
   * sessionStorage (some junto com a aba).
   *
   * O padrão é NÃO lembrar. Este token altera chamado e dispara mensagem de
   * WhatsApp para uma pessoa real - numa máquina compartilhada, deixá-lo
   * gravado é entregar isso para quem sentar depois.
   */
  function gravarToken(token, lembrar) {
    try {
      sessionStorage.removeItem(CHAVE_TOKEN);
      localStorage.removeItem(CHAVE_TOKEN);
      if (!token) return;
      (lembrar ? localStorage : sessionStorage).setItem(CHAVE_TOKEN, token);
    } catch (e) { /* sem armazenamento: o token vale só para esta página */ }
  }

  function temToken() {
    // Com o token no servidor o quadro está sempre conectado: o `Authorization`
    // que sai daqui é descartado e substituído no proxy.
    if (tokenNoServidor()) return true;
    return lerToken() !== '';
  }

  function lembrando() {
    try {
      return localStorage.getItem(CHAVE_TOKEN) !== null;
    } catch (e) {
      return false;
    }
  }

  // Preenchimento automático: servidor-painel.mjs injeta o PAINEL_TOKEN (ou o
  // INTERNAL_API_TOKEN, se aquele não existir) via /painel-token.js, carregado
  // ANTES deste arquivo. Decisão explícita de trocar a pergunta manual do
  // token por conexão automática - quem alcançar esta porta na rede também
  // herda a credencial sem digitar nada. Ver README do painel.
  if (window.PAINEL_TOKEN_AUTO && !temToken()) {
    gravarToken(window.PAINEL_TOKEN_AUTO, false);
  }

  /* ---------- Preferência de aviso ------------------------------------- */

  // Padrão ligado: mover um chamado avisa o usuário no WhatsApp.
  function avisarUsuario() {
    return prefs.avisar !== false;
  }

  function definirAvisarUsuario(valor) {
    prefs.avisar = !!valor;
    gravarPrefs(prefs);
  }

  /* ---------- Chamadas ------------------------------------------------- */

  /**
   * Quando o servidor do painel injeta o token, não há o que pedir ao
   * atendente.
   *
   * `window.PAINEL_SERVIDOR` vem de `/painel-servidor.js`, gerado pelo
   * `servidor-painel.mjs`. Ele carrega a DECISÃO, nunca o token: nesse modo o
   * token não chega ao navegador, que é metade do motivo de tirá-lo daqui.
   */
  function tokenNoServidor() {
    return !!(window.PAINEL_SERVIDOR && window.PAINEL_SERVIDOR.tokenNoServidor);
  }

  function baseUrl() {
    return (window.PAINEL_CONFIG && window.PAINEL_CONFIG.apiBaseUrl) || '';
  }

  function ErroApi(mensagem, status) {
    const err = new Error(mensagem);
    err.status = status;
    return err;
  }

  async function pedir(caminho, opcoes) {
    const opts = opcoes || {};
    let res;

    try {
      res = await fetch(baseUrl() + caminho, {
        method: opts.method || 'GET',
        headers: Object.assign({ Authorization: 'Bearer ' + lerToken() }, opts.headers || {}),
        body: opts.body,
      });
    } catch (e) {
      // Falha de rede e bloqueio de CORS chegam aqui iguais: o navegador não
      // conta qual foi, de propósito. As duas causas prováveis estão na
      // mensagem para não mandar ninguém procurar no lugar errado.
      throw ErroApi('servidor fora do ar ou origem não liberada em PAINEL_ORIGENS', 0);
    }

    // 401 tem duas origens, e o tratamento não pode ser o mesmo:
    //
    //   - do PAINEL, com o cabeçalho abaixo: a sessão do Entra expirou.
    //     Recarregar leva a pessoa ao login em vez de deixar o quadro repetindo
    //     "token recusado" a cada 30 segundos.
    //   - do BOT, repassado pelo proxy: o token da API está errado. Recarregar
    //     aqui daria um laço infinito, porque a página carrega bem.
    //
    // É por isso que o gatilho é o cabeçalho, e não o status sozinho.
    if (res.status === 401) {
      if (res.headers.get('x-painel-sessao') === 'expirada') {
        window.location.reload();
      }
      throw ErroApi('token recusado', 401);
    }

    if (!res.ok) {
      let detalhe = 'HTTP ' + res.status;
      try {
        const corpo = await res.json();
        if (corpo && corpo.erro) detalhe = corpo.erro;
      } catch (e) { /* resposta sem JSON: fica o status */ }
      throw ErroApi(detalhe, res.status);
    }

    return res.json();
  }

  function listarChamados() {
    return pedir('/internal/chamados?limite=500');
  }

  /**
   * Cria uma tarefa: um cartão que nasce aqui, sem conversa de WhatsApp por trás.
   *
   * O corpo usa os MESMOS nomes que a listagem devolve (`nome`, `resumo`,
   * `descricao`) e não o vocabulário do quadro (solicitante/título/descrição). A
   * tradução entre os dois mundos acontece num lugar só, no `paraCartao` abaixo -
   * duas traduções em arquivos diferentes é como elas divergem.
   *
   * `origem` NÃO vai no corpo: o servidor a fixa em 'painel'. Mandar daqui não
   * teria efeito (o Fastify remove campo não declarado no schema) e daria a falsa
   * impressão de que o painel escolhe.
   */
  function criarTarefa(campos) {
    return pedir('/internal/tarefas', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(campos),
    });
  }

  /**
   * Altera a CLASSIFICAÇÃO do chamado: setor, tipo, prioridade, prazo,
   * responsável, canal e os campos dos blocos interno e franquia.
   *
   * Rota separada de `moverChamado` e de `definirAssunto`, e a separação é a
   * mesma dos três no servidor: mover é evento de atendimento (pode avisar o
   * usuário no WhatsApp e move marco de SLA), classificar é organização. Um
   * ajuste de setor não pode disparar mensagem para ninguém.
   *
   * `mudancas` é um objeto com só o que mudou. O servidor trata campo ausente
   * como "não mexa" e `null` como "limpe", e mandar o objeto inteiro apagaria
   * essa distinção.
   *
   * A resposta é o chamado INTEIRO, já no formato da listagem: é o que deixa o
   * quadro repintar cartão e detalhe sem uma segunda ida ao servidor.
   */
  function alterarChamado(chamadoId, mudancas) {
    return pedir('/internal/chamados/' + chamadoId, {
      method: 'PATCH',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(mudancas),
    });
  }

  /** Avaliação pós-fechamento. O servidor recusa fora de resolvido/fechado. */
  function avaliarChamado(chamadoId, nota, comentario) {
    return pedir('/internal/chamados/' + chamadoId + '/avaliacao', {
      method: 'PUT',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ nota: nota, comentario: comentario || null }),
    });
  }

  /* ---------- Detalhe: comentários, anexos, dependências --------------- */

  /**
   * As listas que pendem de UM chamado, buscadas só quando ele é aberto.
   *
   * Não vêm na listagem de propósito: seriam 500 cartões x N comentários x M
   * anexos para desenhar quatro campos por cartão. Etiqueta é a exceção e vem
   * junto, porque aparece NO cartão.
   */
  function carregarDetalhe(chamadoId) {
    return pedir('/internal/chamados/' + chamadoId + '/detalhe');
  }

  function comentar(chamadoId, texto, autor) {
    return pedir('/internal/chamados/' + chamadoId + '/comentarios', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ texto: texto, autor: autor || undefined }),
    });
  }

  // Manda o conjunto INTEIRO de etiquetas, não o delta: o campo da tela é uma
  // caixa de texto, e o que ela sabe dizer é "no fim, são estas".
  function definirTags(chamadoId, tags) {
    return pedir('/internal/chamados/' + chamadoId + '/tags', {
      method: 'PUT',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ tags: tags }),
    });
  }

  /**
   * Sobe um anexo em base64 dentro do JSON.
   *
   * O servidor não fala `multipart` - é uma rota só, e adicionar
   * `@fastify/multipart` por causa dela mudaria o formato de corpo de um
   * servidor que hoje é JSON de ponta a ponta. O preço é a inflação de 4/3 do
   * base64, e o `bodyLimit` daquela rota já está dimensionado para ela.
   */
  function enviarAnexo(chamadoId, arquivo, enviadoPor) {
    return new Promise(function (resolve, reject) {
      const leitor = new FileReader();

      leitor.onerror = function () {
        reject(ErroApi('não foi possível ler o arquivo', 0));
      };

      leitor.onload = function () {
        // `readAsDataURL` devolve "data:<mime>;base64,<dados>" - o servidor quer
        // só a segunda metade, e o mime vem do próprio File (mais confiável que
        // reparsear o prefixo).
        const bruto = String(leitor.result);
        const virgula = bruto.indexOf(',');
        if (virgula === -1) {
          reject(ErroApi('arquivo ilegível', 0));
          return;
        }

        pedir('/internal/chamados/' + chamadoId + '/anexos', {
          method: 'POST',
          headers: { 'content-type': 'application/json' },
          body: JSON.stringify({
            nome: arquivo.name,
            // Alguns navegadores devolvem `type` vazio para extensão que não
            // conhecem; o servidor recusa com a lista do que aceita, que é uma
            // mensagem melhor do que "tipo vazio".
            mime: arquivo.type || 'application/octet-stream',
            conteudoBase64: bruto.slice(virgula + 1),
            enviadoPor: enviadoPor || undefined,
          }),
        }).then(resolve, reject);
      };

      leitor.readAsDataURL(arquivo);
    });
  }

  /**
   * O endereço de download de um anexo.
   *
   * Só serve quando o token está NO SERVIDOR (`PAINEL_SERVIDOR.tokenNoServidor`):
   * aí o proxy põe o `Authorization` e um link comum funciona. Com o token no
   * navegador não há como assiná-lo numa navegação de link, e quem baixa é o
   * `baixarAnexo` abaixo, via fetch.
   */
  function urlAnexo(anexoId) {
    return baseUrl() + '/internal/anexos/' + anexoId;
  }

  /**
   * Baixa o anexo pelo fetch e devolve um Blob.
   *
   * Existe porque `<a href>` não carrega cabeçalho: sem o token no servidor, um
   * link direto levaria 401. Passando pelo fetch, o `Authorization` vai do mesmo
   * jeito que em toda outra chamada, e a tela transforma o Blob num download.
   */
  async function baixarAnexo(anexoId) {
    let res;
    try {
      res = await fetch(urlAnexo(anexoId), {
        headers: { Authorization: 'Bearer ' + lerToken() },
      });
    } catch (e) {
      throw ErroApi('servidor fora do ar ou origem não liberada em PAINEL_ORIGENS', 0);
    }
    if (!res.ok) throw ErroApi('HTTP ' + res.status, res.status);
    return res.blob();
  }

  function excluirAnexo(anexoId) {
    return pedir('/internal/anexos/' + anexoId, { method: 'DELETE' });
  }

  // A direção está no nome da rota: `chamadoId` é sempre o TRAVADO. Para dizer o
  // contrário, chama-se com os dois trocados.
  function criarDependencia(chamadoId, bloqueadorId) {
    return pedir('/internal/chamados/' + chamadoId + '/dependencias', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ bloqueadorId: bloqueadorId }),
    });
  }

  function removerDependencia(chamadoId, bloqueadorId) {
    return pedir('/internal/chamados/' + chamadoId + '/dependencias/' + bloqueadorId, {
      method: 'DELETE',
    });
  }

  /* ---------- Setores -------------------------------------------------- */

  /**
   * A lista de áreas da empresa (TI, Financeiro, Operações...).
   *
   * Mora no banco e não num enum, pela mesma razão dos assuntos: organograma
   * muda por decisão de negócio, e enum do Prisma só muda com migração e deploy.
   * Editar aqui vale para todo mundo no chamado seguinte.
   *
   * NÃO é a lista de assuntos: assunto é o que o cliente escolhe no menu do
   * WhatsApp, setor é quem atende. Ver o cabeçalho de `internal/setores.ts`.
   */
  function listarSetores() {
    return pedir('/internal/setores');
  }

  function criarSetor(dados) {
    return pedir('/internal/setores', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(dados),
    });
  }

  function atualizarSetor(id, mudancas) {
    return pedir('/internal/setores/' + id, {
      method: 'PATCH',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(mudancas),
    });
  }

  function excluirSetor(id) {
    return pedir('/internal/setores/' + id, { method: 'DELETE' });
  }

  function moverChamado(id, situacao, avisar) {
    return pedir('/internal/chamados/' + id + '/situacao', {
      method: 'PATCH',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ situacao: situacao, notificarUsuario: !!avisar }),
    });
  }

  /**
   * Troca o assunto do chamado.
   *
   * Rota separada da de situação no servidor, e separada aqui pelo mesmo motivo:
   * mover um cartão é evento de atendimento (pode avisar o usuário no WhatsApp,
   * move marco de SLA), classificar é correção. Uma correção de assunto não pode
   * disparar mensagem para ninguém.
   */
  function definirAssunto(chamadoId, categoriaId) {
    return pedir('/internal/chamados/' + chamadoId + '/categoria', {
      method: 'PATCH',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ categoriaId: categoriaId }),
    });
  }

  /* ---------- Assuntos (árvore de categorias) -------------------------- */

  function listarAssuntos() {
    return pedir('/internal/categorias');
  }

  function criarAssunto(dados) {
    return pedir('/internal/categorias', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(dados),
    });
  }

  // Só o que mudou vai no corpo: o servidor trata campo ausente como "não mexa",
  // e `paiId: null` como "promova para raiz". Mandar o objeto inteiro apagaria
  // essa distinção.
  function atualizarAssunto(id, mudancas) {
    return pedir('/internal/categorias/' + id, {
      method: 'PATCH',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(mudancas),
    });
  }

  function excluirAssunto(id) {
    return pedir('/internal/categorias/' + id, { method: 'DELETE' });
  }

  /** `desde` em ISO, ou vazio para o histórico inteiro. */
  function carregarMetricas(desde) {
    return pedir('/internal/metricas' + (desde ? '?desde=' + encodeURIComponent(desde) : ''));
  }

  /**
   * A série temporal do dashboard: um ponto por balde de tempo.
   *
   * O `tz` vai junto e não é enfeite. As datas moram em UTC no banco, e "dia" é
   * um conceito local: sem mandar o deslocamento de quem está olhando, um
   * chamado aberto às 21h de terça em UTC-3 seria contado na quarta, e o pico do
   * fim da tarde apareceria sempre no dia seguinte.
   *
   * `balde` vazio deixa o servidor escolher a resolução pelo tamanho da janela.
   */
  function carregarSerie(desde, balde) {
    var q = ['tz=' + new Date().getTimezoneOffset()];
    if (desde) q.push('desde=' + encodeURIComponent(desde));
    if (balde) q.push('balde=' + encodeURIComponent(balde));
    return pedir('/internal/series?' + q.join('&'));
  }

  /* ---------- Pessoas -------------------------------------------------- */

  /**
   * O cadastro de pessoas mora no banco, e não no navegador.
   *
   * Antes ele vivia no `localStorage` (`painel-chamados.v1`), o que fazia cada
   * atendente manter um cadastro só seu: quem você acrescentava aqui ninguém
   * mais via. Estas quatro rotas são o que torna a lista uma coisa só para
   * todo mundo.
   *
   * O vocabulário do servidor é `nome`/`cor`; o do quadro é `name`/`color`. A
   * tradução acontece num lugar só, no app.js, pelo mesmo motivo de
   * `paraCartao`: duas traduções em arquivos diferentes é como elas divergem.
   */
  function listarPessoas() {
    return pedir('/internal/pessoas');
  }

  /* ---------- Configuração do painel ----------------------------------- */

  /**
   * Identidade do painel e rótulos do período — antes no `localStorage`, agora
   * no banco, pelo mesmo motivo das pessoas: era a última coisa ajustável na
   * tela que cada navegador guardava só para si.
   */
  function carregarConfiguracao() {
    return pedir('/internal/configuracao');
  }

  // Só o campo que mudou vai no corpo: o servidor trata ausente como "não
  // mexa". Mandar o objeto inteiro faria duas pessoas editando ao mesmo tempo
  // uma sobrescrever o trabalho da outra com o estado da própria tela.
  function salvarConfiguracao(mudancas) {
    return pedir('/internal/configuracao', {
      method: 'PATCH',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(mudancas),
    });
  }

  function criarPessoa(dados) {
    return pedir('/internal/pessoas', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(dados),
    });
  }

  // Manda nome e cor sempre, e não só o que mudou: a gravação é adiada e pode
  // juntar as duas edições numa chamada. Um PATCH idempotente com o estado
  // atual da linha é mais simples de acertar do que um delta acumulado.
  function atualizarPessoa(id, dados) {
    return pedir('/internal/pessoas/' + id, {
      method: 'PATCH',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(dados),
    });
  }

  function excluirPessoa(id) {
    return pedir('/internal/pessoas/' + id, { method: 'DELETE' });
  }

  /* ---------- Tradução: chamado -> cartão ------------------------------ */

  /**
   * As colunas do quadro usam os MESMOS valores de `situacao` do banco
   * (aberto / em_andamento / resolvido / cancelado). Por isso não existe tabela
   * de conversão aqui: `status` é a situação, sem intermediário que possa
   * divergir. Ver as colunas em data.js.
   */
  function paraCartao(c) {
    return {
      key: '#' + c.id,
      chamadoId: c.id,
      title: c.resumo,
      descricao: c.descricao,
      solicitante: c.nome,
      // 'whatsapp' ou 'painel'. O quadro usa isto para NÃO oferecer o aviso ao
      // solicitante numa tarefa: ela não tem telefone, então o pedido de aviso
      // seria aceito e não enviaria nada (o servidor registra um warn e devolve
      // `notificado: false`).
      origem: c.origem,
      status: c.situacao,
      abertoEm: c.dataAbertura,
      atualizadoEm: c.atualizadoEm,
      // O ID do assunto, não o texto. Quem traduz para rótulo é o quadro, com a
      // árvore que ele já carregou — uma cópia do texto aqui divergiria na
      // primeira renomeação.
      categoriaId: c.categoriaId === undefined ? null : c.categoriaId,
      // Os marcos de SLA. `null` enquanto não aconteceram, e o quadro mostra "—"
      // em vez de inventar uma duração.
      primeiroAtendimentoEm: c.primeiroAtendimentoEm || null,
      resolvidoEm: c.resolvidoEm || null,

      // --- Classificação ---------------------------------------------------
      //
      // Os 24 campos viajam com o MESMO NOME do banco, sem tradução. É o oposto
      // do que `title`/`solicitante`/`status` fazem acima, e a diferença é
      // deliberada: aqueles três nomes vinham do quadro genérico e já existiam
      // quando os chamados chegaram. Para os campos novos, um segundo vocabulário
      // só criaria um dicionário para manter — e o PATCH que os grava usa os
      // nomes do banco de qualquer forma.
      tipo: c.tipo || null,
      setorId: c.setorId === undefined ? null : c.setorId,
      prioridade: c.prioridade || 'media',
      canal: c.canal || 'whatsapp',
      contato: c.contato || null,
      responsavelId: c.responsavelId === undefined ? null : c.responsavelId,
      prazoEm: c.prazoEm || null,

      setorOrigemId: c.setorOrigemId === undefined ? null : c.setorOrigemId,
      tipoSolicitacao: c.tipoSolicitacao || null,
      impacto: c.impacto || null,
      sistemaAfetado: c.sistemaAfetado || null,
      // `== null` e não `||`: zero é um tempo informado ("não gastei nada
      // ainda"), e `|| null` o transformaria em "não informado".
      tempoEstimadoMin: c.tempoEstimadoMin == null ? null : c.tempoEstimadoMin,
      tempoGastoMin: c.tempoGastoMin == null ? null : c.tempoGastoMin,

      franquiaCodigo: c.franquiaCodigo || null,
      franquiaNome: c.franquiaNome || null,
      franqueadoNome: c.franqueadoNome || null,
      franqueadoContato: c.franqueadoContato || null,
      localizacao: c.localizacao || null,
      tipoFranquia: c.tipoFranquia || null,
      afetaAtendimento: !!c.afetaAtendimento,
      envolveCusto: !!c.envolveCusto,
      valorEstimadoCentavos:
        c.valorEstimadoCentavos == null ? null : c.valorEstimadoCentavos,
      precisaAprovacao: !!c.precisaAprovacao,
      urgenciaComercial: c.urgenciaComercial || null,

      avaliacaoNota: c.avaliacaoNota == null ? null : c.avaliacaoNota,
      avaliacaoComentario: c.avaliacaoComentario || null,
      avaliadoEm: c.avaliadoEm || null,

      // Etiquetas já como texto: diferente de setor e assunto, tag não tem lista
      // carregada para resolver id -> nome, e o nome É o identificador.
      tags: c.tags || [],

      // O quadro genérico espera este campo existir; chamado não tem "label"
      // além das etiquetas acima.
      labels: [],
    };
  }

  window.PainelApi = {
    listarChamados: listarChamados,
    criarTarefa: criarTarefa,
    moverChamado: moverChamado,
    definirAssunto: definirAssunto,
    alterarChamado: alterarChamado,
    avaliarChamado: avaliarChamado,
    carregarDetalhe: carregarDetalhe,
    comentar: comentar,
    definirTags: definirTags,
    enviarAnexo: enviarAnexo,
    // `urlAnexo` fica de fora de propósito: ela monta o endereço, mas quem baixa
    // é `baixarAnexo` (o download precisa do cabeçalho de token, e link não o
    // carrega). Exportar as duas ofereceria um caminho que dá 401.
    baixarAnexo: baixarAnexo,
    excluirAnexo: excluirAnexo,
    criarDependencia: criarDependencia,
    removerDependencia: removerDependencia,
    listarSetores: listarSetores,
    criarSetor: criarSetor,
    atualizarSetor: atualizarSetor,
    excluirSetor: excluirSetor,
    listarAssuntos: listarAssuntos,
    criarAssunto: criarAssunto,
    atualizarAssunto: atualizarAssunto,
    excluirAssunto: excluirAssunto,
    carregarMetricas: carregarMetricas,
    carregarSerie: carregarSerie,
    carregarConfiguracao: carregarConfiguracao,
    salvarConfiguracao: salvarConfiguracao,
    listarPessoas: listarPessoas,
    criarPessoa: criarPessoa,
    atualizarPessoa: atualizarPessoa,
    excluirPessoa: excluirPessoa,
    paraCartao: paraCartao,
    lerToken: lerToken,
    gravarToken: gravarToken,
    temToken: temToken,
    tokenNoServidor: tokenNoServidor,
    lembrando: lembrando,
    avisarUsuario: avisarUsuario,
    definirAvisarUsuario: definirAvisarUsuario,
  };
})();
