import {
  analyzeDocument,
  deleteDocument,
  documentById,
  documents,
  health,
  researchTopic,
  reviewFlashcard,
  searchDocuments,
  stats,
  uploadDocument,
} from "./api.js";

const refs = {
  modelName: document.querySelector("#modelName"),
  totalDocuments: document.querySelector("#totalDocuments"),
  totalFlashcards: document.querySelector("#totalFlashcards"),
  dueReviews: document.querySelector("#dueReviews"),
  studyProgress: document.querySelector("#studyProgress"),
  reviewQueue: document.querySelector("#reviewQueue"),
  reviewQueueCount: document.querySelector("#reviewQueueCount"),
  recentDocuments: document.querySelector("#recentDocuments"),
  documents: document.querySelector("#documents"),
  reviewDocuments: document.querySelector("#reviewDocuments"),
  documentCount: document.querySelector("#documentCount"),
  detail: document.querySelector("#detail"),
  selectedName: document.querySelector("#selectedName"),
  uploadForm: document.querySelector("#uploadForm"),
  chooseFileButton: document.querySelector("#chooseFileButton"),
  fileInput: document.querySelector("#fileInput"),
  fileName: document.querySelector("#fileName"),
  uploadStatus: document.querySelector("#uploadStatus"),
  searchForm: document.querySelector("#searchForm"),
  searchInput: document.querySelector("#searchInput"),
  researchForm: document.querySelector("#researchForm"),
  researchInput: document.querySelector("#researchInput"),
  researchResults: document.querySelector("#researchResults"),
  tabButtons: document.querySelectorAll("[data-tab-button]"),
  tabViews: document.querySelectorAll("[data-tab]"),
  filters: document.querySelectorAll("[data-filter]"),
};

let state = {
  docs: [],
  filteredDocs: [],
  selectedId: null,
  selectedFile: null,
  activeFilter: "all",
};

async function boot() {
  const status = await health();
  refs.modelName.textContent = status.model;
  bindEvents();
  await refreshAll();
}

function bindEvents() {
  refs.tabButtons.forEach((button) => {
    button.addEventListener("click", () => setTab(button.dataset.tabButton));
  });

  refs.filters.forEach((button) => {
    button.addEventListener("click", () => {
      state.activeFilter = button.dataset.filter;
      renderAll();
    });
  });

  refs.uploadForm.addEventListener("submit", uploadSelectedFile);
  refs.chooseFileButton.addEventListener("click", () => refs.fileInput.click());
  refs.fileInput.addEventListener("change", () => setSelectedFile(refs.fileInput.files?.[0] || null));

  refs.uploadForm.addEventListener("dragover", (event) => {
    event.preventDefault();
    refs.uploadForm.classList.add("is-dragging");
  });
  refs.uploadForm.addEventListener("dragleave", () => refs.uploadForm.classList.remove("is-dragging"));
  refs.uploadForm.addEventListener("drop", (event) => {
    event.preventDefault();
    refs.uploadForm.classList.remove("is-dragging");
    setSelectedFile(event.dataTransfer.files?.[0] || null);
  });

  refs.searchForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const query = refs.searchInput.value.trim();
    state.filteredDocs = query ? await searchDocuments(query) : state.docs;
    state.activeFilter = "all";
    setTab("library");
    renderAll();
  });

  refs.researchForm.addEventListener("submit", searchResearch);
  document.body.addEventListener("click", handleDocumentActions);
}

async function refreshAll() {
  const [summary, docs] = await Promise.all([stats(), documents()]);
  state.docs = docs;
  state.filteredDocs = docs;
  refs.totalDocuments.textContent = summary.totalDocuments || 0;
  refs.totalFlashcards.textContent = summary.totalFlashcards || 0;
  refs.dueReviews.textContent = summary.dueReviews || 0;
  refs.studyProgress.textContent = `${summary.reviewedCards || 0}/${summary.totalFlashcards || 0}`;
  renderAll();
}

function renderAll() {
  const docs = filteredDocs();
  renderDocuments(refs.documents, docs, { deleteButton: true });
  renderDocuments(refs.reviewDocuments, state.docs, { compact: true });
  renderDocuments(refs.recentDocuments, state.docs.slice(0, 4), { deleteButton: false });
  renderQueue();
  refs.documentCount.textContent = `${docs.length} materiais`;

  refs.filters.forEach((button) => {
    button.classList.toggle("active", button.dataset.filter === state.activeFilter);
  });
}

function filteredDocs() {
  const source = state.filteredDocs.length || refs.searchInput.value.trim() ? state.filteredDocs : state.docs;
  if (state.activeFilter === "pdf") {
    return source.filter((doc) => doc.fileName.toLowerCase().endsWith(".pdf"));
  }
  if (state.activeFilter === "due") {
    return source.filter((doc) => (doc.study?.progress?.dueCards || 0) > 0);
  }
  return source;
}

function renderDocuments(target, docs, options = {}) {
  target.innerHTML = docs.length
    ? docs.map((doc) => documentCard(doc, options)).join("")
    : `<div class="empty-state">Nenhum material encontrado.</div>`;
}

function documentCard(doc, options = {}) {
  const progress = doc.study?.progress || {};
  const isPDF = doc.fileName.toLowerCase().endsWith(".pdf");
  return `
    <article class="doc-card ${doc.id === state.selectedId ? "active" : ""}" data-id="${doc.id}">
      <div class="doc-card-top">
        <span class="file-badge ${isPDF ? "pdf" : ""}">${isPDF ? "PDF" : "ARQ"}</span>
        ${options.deleteButton ? `<button type="button" class="icon-danger" data-delete="${doc.id}" title="Apagar">Excluir</button>` : ""}
      </div>
      <h3>${escapeHTML(doc.fileName)}</h3>
      <p>${escapeHTML(doc.study?.title || doc.preview || "Material pronto para estudo.")}</p>
      <div class="progress-bar"><span style="width:${progress.completion || 0}%"></span></div>
      <div class="chips">
        <span class="chip">${progress.totalCards || 0} cards</span>
        <span class="chip">${progress.dueCards || 0} revisar</span>
        ${(doc.insight?.tags || []).slice(0, options.compact ? 1 : 3).map((tag) => `<span class="chip">${escapeHTML(tag)}</span>`).join("")}
      </div>
    </article>
  `;
}

function renderQueue() {
  const dueCards = [];
  for (const doc of state.docs) {
    for (const card of doc.study?.flashcards || []) {
      if (new Date(card.dueDate) <= new Date()) {
        dueCards.push({ doc, card });
      }
    }
  }
  refs.reviewQueueCount.textContent = `${dueCards.length} pendentes`;
  refs.reviewQueue.innerHTML = dueCards.length
    ? dueCards.slice(0, 8).map(({ doc, card }) => `
      <article class="queue-card">
        <span>${escapeHTML(doc.fileName)}</span>
        <strong>${escapeHTML(card.question)}</strong>
        <button type="button" data-open="${doc.id}">Abrir revisão</button>
      </article>
    `).join("")
    : `<div class="empty-state">Nenhuma revisão pendente agora.</div>`;
}

async function selectDocument(id) {
  state.selectedId = id;
  const doc = await documentById(id);
  refs.selectedName.textContent = doc.fileName;
  refs.detail.innerHTML = renderDetail(doc);
  renderAll();
  setTab("review");
}

function renderDetail(doc) {
  const insight = doc.insight || {};
  const study = doc.study || {};
  const progress = study.progress || {};
  return `
    <div class="detail-content">
      <div class="detail-actions">
        <button type="button" class="ghost-button" data-reanalyze="${doc.id}">Recriar plano</button>
        <button type="button" class="ghost-button danger" data-delete="${doc.id}">Apagar arquivo</button>
      </div>
      <div class="study-hero">
        <div>
          <span>Plano de estudos</span>
          <h3>${escapeHTML(study.title || doc.fileName)}</h3>
          <p>${escapeHTML(insight.summary || "Material importado para revisao.")}</p>
        </div>
        <strong>${progress.completion || 0}%</strong>
      </div>
      <section class="study-metrics">
        <article><span>Cards</span><strong>${progress.totalCards || 0}</strong></article>
        <article><span>Pendentes</span><strong>${progress.dueCards || 0}</strong></article>
        <article><span>Tempo</span><strong>${progress.estimatedMinutes || study.estimatedMinutes || 0}m</strong></article>
      </section>
      <section class="insight-section">
        <h3>Objetivos</h3>
        <ol class="actions-list">${(study.objectives || []).map((item) => `<li>${escapeHTML(item)}</li>`).join("")}</ol>
      </section>
      <section class="insight-section">
        <h3>Agenda de revisão espaçada</h3>
        <div class="timeline">${(study.schedule || []).map(scheduleItem).join("")}</div>
      </section>
      <section class="insight-section">
        <h3>Tópicos principais</h3>
        <div class="topic-grid">${(study.topics || []).map(topicCard).join("")}</div>
      </section>
      <section class="insight-section">
        <h3>Flashcards</h3>
        <div class="flashcards">${(study.flashcards || []).map((card) => flashcard(doc.id, card)).join("")}</div>
      </section>
      <section class="insight-section">
        <h3>Texto extraído</h3>
        <p class="summary">${escapeHTML(truncate(doc.text || "", 1600))}</p>
      </section>
    </div>
  `;
}

function scheduleItem(item) {
  return `<article class="timeline-item"><strong>${escapeHTML(formatDate(item.dueDate))}</strong><span>${escapeHTML(item.title)}</span><small>${item.durationMinutes} min</small></article>`;
}

function topicCard(topic) {
  return `<article class="topic-card"><span>${escapeHTML(topic.priority || "media")}</span><strong>${escapeHTML(topic.name)}</strong><p>${escapeHTML(topic.summary)}</p></article>`;
}

function flashcard(documentId, card) {
  const due = new Date(card.dueDate) <= new Date();
  return `
    <article class="flashcard ${due ? "due" : ""}">
      <div>
        <span>${due ? "revisar agora" : `próxima: ${escapeHTML(formatDate(card.dueDate))}`}</span>
        <h4>${escapeHTML(card.question)}</h4>
        <p>${escapeHTML(card.answer)}</p>
      </div>
      <div class="review-actions">
        <button type="button" class="ghost-button" data-review="${documentId}" data-card="${card.id}" data-result="again">Rever</button>
        <button type="button" class="ghost-button" data-review="${documentId}" data-card="${card.id}" data-result="hard">Difícil</button>
        <button type="button" data-review="${documentId}" data-card="${card.id}" data-result="good">Acertei</button>
      </div>
    </article>
  `;
}

async function uploadSelectedFile(event) {
  event.preventDefault();
  if (!state.selectedFile) {
    refs.uploadStatus.textContent = "Escolha um arquivo para analisar.";
    refs.fileInput.click();
    return;
  }
  refs.uploadStatus.textContent = "Extraindo texto, gerando plano e flashcards...";
  refs.uploadForm.classList.add("is-uploading");
  try {
    const doc = await uploadDocument(state.selectedFile);
    refs.uploadStatus.textContent = "Material pronto para estudar.";
    refs.fileInput.value = "";
    setSelectedFile(null);
    await refreshAll();
    await selectDocument(doc.id);
  } catch (error) {
    refs.uploadStatus.textContent = `Falha: ${error.message}`;
  } finally {
    refs.uploadForm.classList.remove("is-uploading");
  }
}

async function searchResearch(event) {
  event.preventDefault();
  const query = refs.researchInput.value.trim();
  if (!query) return;
  refs.researchResults.innerHTML = `<div class="empty-state">Buscando sugestões...</div>`;
  try {
    const result = await researchTopic(query);
    refs.researchResults.innerHTML = renderResearch(result);
  } catch (error) {
    refs.researchResults.innerHTML = `<div class="empty-state">Não foi possível pesquisar agora: ${escapeHTML(error.message)}</div>`;
  }
}

function renderResearch(result) {
  return `
    <section class="research-block">
      <h3>Consultas úteis</h3>
      <div class="chips">${(result.pdfQueries || []).map((item) => `<span class="chip">${escapeHTML(item)}</span>`).join("")}</div>
    </section>
    <section class="research-links">
      ${(result.results || []).map((item) => `
        <a href="${escapeHTML(item.url)}" target="_blank" rel="noreferrer" class="research-card">
          <span>${escapeHTML(item.type)}</span>
          <strong>${escapeHTML(item.title)}</strong>
          <p>${escapeHTML(item.note)}</p>
        </a>
      `).join("")}
    </section>
  `;
}

async function handleDocumentActions(event) {
  const deleteButton = event.target.closest("[data-delete]");
  if (deleteButton) {
    event.stopPropagation();
    if (!confirm("Apagar este arquivo, texto extraído, plano e revisões?")) return;
    await deleteDocument(deleteButton.dataset.delete);
    state.selectedId = null;
    refs.selectedName.textContent = "Selecione um material";
    refs.detail.innerHTML = `<div class="empty-state">Nenhum material selecionado.</div>`;
    await refreshAll();
    return;
  }

  const reanalyzeButton = event.target.closest("[data-reanalyze]");
  if (reanalyzeButton) {
    refs.detail.innerHTML = `<div class="empty-state">Recriando plano com IA...</div>`;
    const doc = await analyzeDocument(reanalyzeButton.dataset.reanalyze);
    refs.detail.innerHTML = renderDetail(doc);
    await refreshAll();
    return;
  }

  const openButton = event.target.closest("[data-open]");
  if (openButton) {
    await selectDocument(openButton.dataset.open);
    return;
  }

  const reviewButton = event.target.closest("[data-review]");
  if (reviewButton) {
    const doc = await reviewFlashcard(reviewButton.dataset.review, reviewButton.dataset.card, reviewButton.dataset.result);
    refs.detail.innerHTML = renderDetail(doc);
    await refreshAll();
    return;
  }

  const card = event.target.closest("[data-id]");
  if (card) {
    await selectDocument(card.dataset.id);
  }
}

function setTab(tab) {
  refs.tabButtons.forEach((button) => button.classList.toggle("active", button.dataset.tabButton === tab));
  refs.tabViews.forEach((view) => view.classList.toggle("active", view.dataset.tab === tab));
}

function setSelectedFile(file) {
  state.selectedFile = file;
  refs.fileName.textContent = file ? `${file.name} (${formatBytes(file.size)})` : "Nenhum arquivo escolhido";
  refs.uploadStatus.textContent = file ? "Arquivo pronto para envio." : "";
}

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function formatDate(value) {
  if (!value) return "sem data";
  return new Intl.DateTimeFormat("pt-BR", { day: "2-digit", month: "2-digit" }).format(new Date(value));
}

function truncate(value, limit) {
  const text = String(value).replace(/\s+/g, " ").trim();
  if (text.length <= limit) return text;
  return `${text.slice(0, limit - 1)}...`;
}

function escapeHTML(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

boot().catch((error) => {
  refs.uploadStatus.textContent = "Backend offline.";
  console.error(error);
});
