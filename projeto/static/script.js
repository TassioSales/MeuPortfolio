// Navegação entre seções GLOBAL
function showSection(sectionId) {
    document.querySelectorAll('.section').forEach(sec => sec.style.display = 'none');
    document.getElementById(sectionId).style.display = 'block';
    document.querySelectorAll('.msg').forEach(msg => msg.textContent = '');
    if(sectionId === 'visualizarSection') {
        document.getElementById('conteudoVisualizado').textContent = '';
    }
    if(sectionId === 'resumoSection') {
        document.getElementById('resumoGerado').textContent = '';
    }
    // Destacar botão ativo
    document.querySelectorAll('.sidebar-btn').forEach(btn => btn.classList.remove('sidebar-active'));
    const idx = {
        'manualSection': 0,
        'uploadSection': 1,
        'visualizarSection': 2,
        'resumoSection': 3,
        'sentimentoSection': 4,
        'inteligenteSection': 5,
        'chatbotSection': 6
    }[sectionId];
    if (typeof idx !== 'undefined') {
        document.querySelectorAll('.sidebar-btn')[idx].classList.add('sidebar-active');
    }
}

// Inicialização: mostra a primeira seção
showSection('manualSection');

document.addEventListener('DOMContentLoaded', () => {
  const uploadForm = document.getElementById('uploadForm');
  const manualForm = document.getElementById('manualForm');
  const textoManualInput = document.getElementById('textoManual');
  const sucessoMensagem = document.getElementById('sucessoMensagem');
  const erroMensagem = document.getElementById('erroMensagem');
  const visualizarBtn = document.getElementById('visualizarBtn');
  const resumoBtn = document.getElementById('resumoBtn');
  const tipoVisualizacao = document.getElementById('tipoVisualizacao');
  const copiarResumoBtn = document.getElementById('copiarResumoBtn');
  const baixarResumoBtn = document.getElementById('baixarResumoBtn');
  const resumoDiv = document.getElementById('resumoGerado');
  const sentimentoBtn = document.getElementById('sentimentoBtn');

  // Envio de texto manual
  manualForm.addEventListener('submit', async function(e) {
      e.preventDefault();
      const texto = textoManualInput.value;
      const formData = new FormData();
      formData.append('texto', texto);
      const resp = await fetch('/manual', { method: 'POST', body: formData });
      const data = await resp.json();
      document.getElementById('manualMsg').textContent = data.mensagem || data.erro || data.status;
  });

  // Upload de arquivo
  uploadForm.addEventListener('submit', async function(e) {
      e.preventDefault();
      const fileInput = document.getElementById('arquivoUpload');
      if(!fileInput.files[0]) {
          document.getElementById('uploadMsg').textContent = 'Selecione um arquivo.';
          return;
      }
      const formData = new FormData();
      formData.append('file', fileInput.files[0]);
      const resp = await fetch('/upload', { method: 'POST', body: formData });
      const data = await resp.json();
      document.getElementById('uploadMsg').textContent = data.mensagem || data.erro || data.status;
  });

  // Visualizar texto salvo
  visualizarBtn.addEventListener('click', async function() {
      const tipo = tipoVisualizacao.value;
      const resp = await fetch(`/visualizar?tipo=${tipo}`);
      const data = await resp.json();
      if(data.status === 'sucesso') {
          try {
              const obj = JSON.parse(data.conteudo);
              document.getElementById('conteudoVisualizado').textContent = obj.conteudo;
          } catch {
              document.getElementById('conteudoVisualizado').textContent = data.conteudo;
          }
          document.getElementById('visualizarMsg').textContent = '';
      } else {
          document.getElementById('conteudoVisualizado').textContent = '';
          document.getElementById('visualizarMsg').textContent = data.mensagem || data.status;
      }
  });

  // Gerar resumo (placeholder)
  resumoBtn.addEventListener('click', async function() {
      const tipo = document.getElementById('tipoResumo').value;
      const formData = new FormData();
      formData.append('tipo', tipo);
      const resp = await fetch('/resumo', { method: 'POST', body: formData });
      const data = await resp.json();
      if(data.status === 'sucesso') {
          // Exibe o texto completo, preservando quebras de linha e espaços
          resumoDiv.innerHTML = '';
          if(typeof data.resumo === 'string') {
              // Quebra linhas em <br> para garantir exibição fiel
              resumoDiv.innerHTML = data.resumo.replace(/\n/g, '<br>');
          } else {
              resumoDiv.innerHTML = JSON.stringify(data.resumo, null, 2).replace(/\n/g, '<br>');
          }
          document.getElementById('resumoMsg').textContent = '';
      } else {
          document.getElementById('resumoGerado').textContent = '';
          document.getElementById('resumoMsg').textContent = data.mensagem || data.status;
      }
  });

  // --- Função copiar resumo ---
  if (copiarResumoBtn) {
    copiarResumoBtn.addEventListener('click', () => {
      // Remove tags HTML e copia texto puro
      const temp = document.createElement('div');
      temp.innerHTML = resumoDiv.innerHTML;
      const texto = temp.innerText;
      navigator.clipboard.writeText(texto).then(() => {
        copiarResumoBtn.innerHTML = '<span>✅</span> Copiado!';
        setTimeout(() => copiarResumoBtn.innerHTML = '<span>📋</span> Copiar', 1500);
      });
    });
  }

  // --- Função baixar resumo ---
  if (baixarResumoBtn) {
    baixarResumoBtn.addEventListener('click', () => {
      const temp = document.createElement('div');
      temp.innerHTML = resumoDiv.innerHTML;
      const texto = temp.innerText;
      const blob = new Blob([texto], {type: 'text/plain'});
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'resumo.txt';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    });
  }

  // --- Contador de caracteres para texto manual ---
  if(textoManualInput) {
    textoManualInput.addEventListener('input', function() {
      const contador = document.getElementById('contadorCaracteres');
      contador.textContent = `Caracteres: ${textoManualInput.value.length}`;
    });
    // Atualiza ao carregar a página
    document.getElementById('contadorCaracteres').textContent = `Caracteres: ${textoManualInput.value.length}`;
  }

  // Exibir texto completo analisado na caixa de preview da análise de sentimento
  function mostrarPreviewSentimento(texto) {
    const preview = document.getElementById('sentimentoTextoPreview');
    if(texto && texto.length > 0) {
      preview.value = texto;
      preview.style.display = '';
    } else {
      preview.value = '';
      preview.style.display = 'none';
    }
  }

  // Modificar chamada AJAX para mostrar o texto analisado
  function analisarSentimento(tipo) {
    const formData = new FormData();
    formData.append('tipo', tipo);
    fetch('/sentimento', {
      method: 'POST',
      body: formData
    })
      .then(response => response.json())
      .then(data => {
        if(data.status === 'sucesso') {
          mostrarPreviewSentimento(''); // não mostrar preview do texto analisado
          let html = `<b>Sentimento (ML):</b> ${data.sentimento_ml}<br>`;
          html += `<b>Sentimento (TextBlob):</b> ${data.sentimento_textblob} (polaridade: ${data.polaridade.toFixed(2)})<br>`;
          html += `<b>Sentimento (BERT multilíngue):</b> ${data.sentimento_pt} (confiança: ${(data.score_pt*100).toFixed(1)}%)<br>`;
          html += `<b>Sentimento (PySentimiento):</b> ${data.sentimento_pysent} (confiança: ${(data.score_pysent*100).toFixed(1)}%)<br>`;
          html += `<b>Sentimento (XLM-RoBERTa CardiffNLP):</b> ${data.sentimento_cardiff} (confiança: ${(data.score_cardiff*100).toFixed(1)}%)<br>`;
          html += `<b>Explicação:</b> ${data.explicacao}`;
          if(data.aviso) {
            html += `<br><span style='color:#b86e00;font-weight:600'>${data.aviso}</span>`;
          }
          document.getElementById('resultadoSentimento').innerHTML = html;
          document.getElementById('sentimentoMsg').textContent = '';
        } else {
          mostrarPreviewSentimento('');
          document.getElementById('resultadoSentimento').textContent = '';
          document.getElementById('sentimentoMsg').textContent = data.mensagem || data.status;
        }
      })
      .catch(error => {
        mostrarPreviewSentimento('');
        document.getElementById('resultadoSentimento').textContent = '';
        document.getElementById('sentimentoMsg').textContent = 'Erro ao analisar sentimento: ' + error;
      });
  }

  // Atualizar evento do botão para usar a função modificada
  if(document.getElementById('sentimentoBtn')) {
    document.getElementById('sentimentoBtn').onclick = function() {
      const tipo = document.getElementById('tipoSentimento').value;
      analisarSentimento(tipo);
    }
  }

  // --- Análise Inteligente ---
  document.getElementById('inteligenteBtn').onclick = async function() {
    const tipo = document.getElementById('inteligenteTipo').value;
    document.getElementById('inteligenteMsg').textContent = 'Processando...';
    document.getElementById('inteligenteWordCloud').innerHTML = '';
    document.getElementById('inteligenteGrafico').innerHTML = '';
    document.getElementById('inteligenteFrases').innerHTML = '';
    document.getElementById('inteligenteEmocoesFrases').innerHTML = '';
    document.getElementById('inteligenteSentimentoGeral').innerHTML = '';
    document.getElementById('inteligenteEmocaoGeral').innerHTML = '';
    document.getElementById('inteligenteResposta').innerHTML = '';
    try {
      const resp = await fetch('/analise_inteligente', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ tipo })
      });
      const data = await resp.json();
      if(data.status === 'sucesso') {
        document.getElementById('inteligenteMsg').textContent = '';
        document.getElementById('inteligenteWordCloud').innerHTML = `<img src='/${data.wordcloud}?t=${Date.now()}' style='max-width:450px;border:1px solid #ccc'>`;
        document.getElementById('inteligenteGrafico').innerHTML = `<img src='/${data.grafico}?t=${Date.now()}' style='max-width:450px;border:1px solid #ccc'>`;
        // Sentimentos por frase
        let html = '<ul>';
        for(let i=0;i<data.frases.length;i++) {
          html += `<li><b>${data.frases[i]}</b> - ${data.sentimentos[i].label} (${(data.sentimentos[i].score*100).toFixed(1)}%)</li>`;
        }
        html += '</ul>';
        document.getElementById('inteligenteFrases').innerHTML = html;
        // Emoções por frase
        let htmlEmo = '<ul>';
        if(data.emocoes && data.emocoes.length === data.frases.length) {
          for(let i=0;i<data.frases.length;i++) {
            htmlEmo += `<li><b>${data.frases[i]}</b> - ${data.emocoes[i].label} (${(data.emocoes[i].score*100).toFixed(1)}%)</li>`;
          }
        } else {
          htmlEmo += '<li>Não foi possível identificar as emoções por frase.</li>';
        }
        htmlEmo += '</ul>';
        document.getElementById('inteligenteEmocoesFrases').innerHTML = htmlEmo;
        // Sentimento geral
        document.getElementById('inteligenteSentimentoGeral').innerHTML = data.sentimento_geral || '-';
        // Emoção geral
        document.getElementById('inteligenteEmocaoGeral').innerHTML = data.emocao_geral || '-';
        // Resposta contextual
        if(data.resposta_contexto) {
          document.getElementById('inteligenteResposta').innerHTML = `<div style='margin-top:12px'><b>Resposta contextual:</b> ${data.resposta_contexto}</div>`;
        }
      } else {
        document.getElementById('inteligenteMsg').textContent = data.mensagem || 'Erro desconhecido.';
      }
    } catch(e) {
      document.getElementById('inteligenteMsg').textContent = 'Erro ao processar: ' + e;
    }
  }

  // --- Chatbot ---
  const chatForm = document.getElementById('chatForm');
  const chatInput = document.getElementById('chatInput');
  const chatHistory = document.getElementById('chatHistory');
  const chatAviso = document.getElementById('chatAviso');
  const chatTipo = document.getElementById('chatTipo');
  if (chatForm) {
      chatForm.onsubmit = async function(e) {
          e.preventDefault();
          const pergunta = chatInput.value.trim();
          const tipo = chatTipo.value;
          if (!pergunta) return;
          addMessage(pergunta, 'user');
          chatInput.value = '';
          chatAviso.textContent = '';
          try {
              const resp = await fetch('/chatbot', {
                  method: 'POST',
                  headers: {'Content-Type': 'application/json'},
                  body: JSON.stringify({ pergunta, tipo })
              });
              const data = await resp.json();
              if (data.status === 'sucesso') {
                  addMessage(data.resposta, 'bot');
              } else {
                  chatAviso.textContent = data.mensagem || 'Erro ao obter resposta.';
              }
          } catch (err) {
              chatAviso.textContent = 'Erro de comunicação com o servidor.';
          }
      };
      function addMessage(msg, sender) {
          const div = document.createElement('div');
          div.className = 'chat-msg ' + sender;
          div.innerHTML = msg;
          chatHistory.appendChild(div);
          chatHistory.scrollTop = chatHistory.scrollHeight;
      }
  }
});
