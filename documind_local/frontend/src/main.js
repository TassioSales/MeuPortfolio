import { documentById, documents, health, searchDocuments, stats, uploadDocument } from "./api.js";

const refs = {
  modelName: document.querySelector("#modelName"),
  totalDocuments: document.querySelector("#totalDocuments"),
  totalBytes: document.querySelector("#totalBytes"),
  tagCount: document.querySelector("#tagCount"),
  highRisk: document.querySelector("#highRisk"),
  documents: document.querySelector("#documents"),
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
  navLinks: document.querySelectorAll("[data-nav-link]"),
};

let selectedId = null;
let selectedFile = null;

async function boot() {
  const status = await health();
  refs.modelName.textContent = status.model;
  await refreshAll();
}

async function refreshAll(list = null) {
  const [summary, docs] = await Promise.all([stats(), list ? Promise.resolve(list) : documents()]);
  refs.totalDocuments.textContent = summary.totalDocuments;
  refs.totalBytes.textContent = formatBytes(summary.totalBytes);
  refs.tagCount.textContent = Object.keys(summary.tags || {}).length;
  refs.highRisk.textContent = summary.risks?.alto || 0;
  renderDocuments(docs);
}

function renderDocuments(docs) {
  refs.documentCount.textContent = `${docs.length} arquivos`;
  refs.documents.innerHTML = docs.length
    ? docs.map((doc) => documentCard(doc)).join("")
    : `<div class="empty-state">Nenhum documento enviado ainda.</div>`;

  refs.documents.querySelectorAll("[data-id]").forEach((element) => {
    element.addEventListener("click", () => selectDocument(element.dataset.id));
  });
}

function documentCard(doc) {
  const risk = doc.insight?.riskLevel || "medio";
  return `
    <article class="doc-card ${doc.id === selectedId ? "active" : ""}" data-id="${doc.id}">
      <h3>${escapeHTML(doc.fileName)}</h3>
      <p>${escapeHTML(doc.preview || doc.insight?.summary || "Sem preview.")}</p>
      <div class="chips">
        <span class="chip">${escapeHTML(doc.insight?.documentType || "outro")}</span>
        <span class="chip risk-${risk}">risco ${escapeHTML(risk)}</span>
        ${(doc.insight?.tags || []).slice(0, 3).map((tag) => `<span class="chip">${escapeHTML(tag)}</span>`).join("")}
      </div>
    </article>
  `;
}

async function selectDocument(id) {
  selectedId = id;
  const doc = await documentById(id);
  refs.selectedName.textContent = doc.fileName;
  refs.detail.innerHTML = renderDetail(doc);
  setActiveNav("insights");
  renderDocuments(await documents());
}

function renderDetail(doc) {
  const insight = doc.insight || {};
  return `
    <div class="detail-content">
      <div class="summary">${escapeHTML(insight.summary || "Sem resumo.")}</div>
      <section class="insight-section">
        <h3>Tags</h3>
        <div class="chips">${(insight.tags || []).map((tag) => `<span class="chip">${escapeHTML(tag)}</span>`).join("")}</div>
      </section>
      <section class="insight-section">
        <h3>Entidades</h3>
        <div class="chips">${(insight.entities || []).map((entity) => `<span class="chip">${escapeHTML(entity)}</span>`).join("") || `<span class="chip">nenhuma</span>`}</div>
      </section>
      <section class="insight-section">
        <h3>Acoes sugeridas</h3>
        <ol class="actions-list">${(insight.suggestedActions || []).map((action) => `<li>${escapeHTML(action)}</li>`).join("")}</ol>
      </section>
      <section class="insight-section">
        <h3>Texto extraido</h3>
        <p class="summary">${escapeHTML(truncate(doc.text || "", 1400))}</p>
      </section>
    </div>
  `;
}

refs.uploadForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!selectedFile) {
    refs.uploadStatus.textContent = "Escolha um arquivo para analisar.";
    refs.fileInput.click();
    return;
  }
  refs.uploadStatus.textContent = "Enviando e analisando com IA...";
  try {
    refs.uploadForm.classList.add("is-uploading");
    const doc = await uploadDocument(selectedFile);
    refs.uploadStatus.textContent = "Documento analisado.";
    refs.fileInput.value = "";
    setSelectedFile(null);
    await refreshAll();
    await selectDocument(doc.id);
  } catch (error) {
    refs.uploadStatus.textContent = `Falha: ${error.message}`;
    console.error(error);
  } finally {
    refs.uploadForm.classList.remove("is-uploading");
  }
});

refs.chooseFileButton.addEventListener("click", () => {
  refs.fileInput.click();
});

refs.fileInput.addEventListener("change", () => {
  setSelectedFile(refs.fileInput.files?.[0] || null);
});

refs.uploadForm.addEventListener("dragover", (event) => {
  event.preventDefault();
  refs.uploadForm.classList.add("is-dragging");
});

refs.uploadForm.addEventListener("dragleave", () => {
  refs.uploadForm.classList.remove("is-dragging");
});

refs.uploadForm.addEventListener("drop", (event) => {
  event.preventDefault();
  refs.uploadForm.classList.remove("is-dragging");
  setSelectedFile(event.dataTransfer.files?.[0] || null);
});

refs.navLinks.forEach((link) => {
  link.addEventListener("click", (event) => {
    event.preventDefault();
    const target = document.querySelector(`#${link.dataset.navLink}`);
    if (!target) return;
    setActiveNav(link.dataset.navLink);
    target.scrollIntoView({ behavior: "smooth", block: "start" });
  });
});

refs.searchForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const query = refs.searchInput.value.trim();
  const result = query ? await searchDocuments(query) : await documents();
  await refreshAll(result);
});

function setSelectedFile(file) {
  selectedFile = file;
  refs.fileName.textContent = file ? `${file.name} (${formatBytes(file.size)})` : "Nenhum arquivo escolhido";
  refs.uploadStatus.textContent = file ? "Arquivo pronto para envio." : "";
}

function setActiveNav(activeId) {
  refs.navLinks.forEach((link) => {
    link.classList.toggle("active", link.dataset.navLink === activeId);
  });
}

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
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
