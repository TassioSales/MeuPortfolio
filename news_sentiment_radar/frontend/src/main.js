import { drawSentimentChart, drawTimelineChart } from "./chart.js";
import { getArticles, getSummary, refreshNews } from "./api.js";

const refs = {
  updatedAt: document.querySelector("#updatedAt"),
  refreshButton: document.querySelector("#refreshButton"),
  marketPulse: document.querySelector("#marketPulse"),
  dominantSentiment: document.querySelector("#dominantSentiment"),
  coverageMix: document.querySelector("#coverageMix"),
  totalArticles: document.querySelector("#totalArticles"),
  averageScore: document.querySelector("#averageScore"),
  riskIndex: document.querySelector("#riskIndex"),
  alertSector: document.querySelector("#alertSector"),
  sectorFilter: document.querySelector("#sectorFilter"),
  sentimentFilter: document.querySelector("#sentimentFilter"),
  searchInput: document.querySelector("#searchInput"),
  sectorThermometers: document.querySelector("#sectorThermometers"),
  sentimentChart: document.querySelector("#sentimentChart"),
  timelineChart: document.querySelector("#timelineChart"),
  sources: document.querySelector("#sources"),
  entities: document.querySelector("#entities"),
  alerts: document.querySelector("#alerts"),
  articles: document.querySelector("#articlesList"),
  articleCount: document.querySelector("#articleCount"),
};

const state = {
  summary: null,
  articles: [],
};

async function loadDashboard() {
  const [summary, articles] = await Promise.all([getSummary(), getArticles()]);
  state.summary = summary;
  state.articles = articles;
  hydrateSectorFilter(summary.sectors);
  renderDashboard();
}

function renderDashboard() {
  const filtered = filterArticles(state.articles);
  renderSummary(state.summary, filtered);
  renderSources(filtered);
  renderAlerts(state.summary, filtered);
  renderArticles(filtered.slice(0, 36), filtered.length);
}

function renderSummary(summary, filteredArticles) {
  const risk = calculateRisk(summary);
  const alertSector = findAlertSector(summary.sectors);
  refs.updatedAt.textContent = `Atualizado: ${formatDate(summary.updatedAt)}`;
  refs.totalArticles.textContent = summary.totalArticles;
  refs.averageScore.textContent = Number(summary.averageScore).toFixed(2);
  refs.riskIndex.textContent = `${risk}%`;
  refs.alertSector.textContent = alertSector || "-";
  refs.marketPulse.textContent = pulseLabel(summary.averageScore, risk);
  refs.dominantSentiment.textContent = dominantSentiment(summary.sentimentCounts);
  refs.coverageMix.textContent = String(new Set(state.articles.map((article) => article.source)).size);
  renderSectors(summary.sectors);
  renderEntities(summary.topEntities);
  drawSentimentChart(refs.sentimentChart, summary.sentimentCounts);
  drawTimelineChart(refs.timelineChart, filteredArticles);
}

function renderSectors(sectors) {
  refs.sectorThermometers.innerHTML = sectors
    .map((sector) => {
      const normalized = Math.max(0, Math.min(100, 50 + sector.averageScore * 18));
      const color = sector.averageScore > 0 ? "#86efac" : sector.averageScore < 0 ? "#fb7185" : "#fde047";
      return `
        <div class="thermo-row">
          <div class="thermo-label">
            <strong>${sector.sector}</strong>
            <span>${sector.count} noticias</span>
          </div>
          <div class="bar">
            <div class="bar-fill" style="width:${normalized}%; background:${color}; box-shadow: 0 0 18px ${color};"></div>
          </div>
          <div class="score">${sector.averageScore.toFixed(2)}</div>
        </div>
      `;
    })
    .join("");
}

function hydrateSectorFilter(sectors) {
  const current = refs.sectorFilter.value;
  const options = [`<option value="all">Todos</option>`]
    .concat(sectors.map((sector) => `<option value="${sector.sector}">${capitalize(sector.sector)}</option>`));
  refs.sectorFilter.innerHTML = options.join("");
  refs.sectorFilter.value = [...refs.sectorFilter.options].some((option) => option.value === current) ? current : "all";
}

function renderEntities(entities) {
  refs.entities.innerHTML = entities.length
    ? entities.map((entity) => `<span class="entity">${entity.name} ${entity.count}</span>`).join("")
    : `<span class="entity">Sem entidades ainda</span>`;
}

function renderSources(articles) {
  const counts = countBy(articles, "source");
  const max = Math.max(1, ...Object.values(counts));
  refs.sources.innerHTML = Object.entries(counts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 8)
    .map(([source, count]) => `
      <div class="source-row">
        <span>${escapeHTML(source)}</span>
        <div class="mini-bar"><i style="width:${(count / max) * 100}%"></i></div>
        <strong>${count}</strong>
      </div>
    `)
    .join("");
}

function renderAlerts(summary, articles) {
  const negativeShare = summary.totalArticles
    ? Math.round(((summary.sentimentCounts.negativo || 0) / summary.totalArticles) * 100)
    : 0;
  const mostNegative = [...articles].sort((a, b) => a.score - b.score).slice(0, 3);
  const alertSector = findAlertSector(summary.sectors);
  const alerts = [
    {
      title: `${negativeShare}% negativas`,
      body: "Percentual de noticias com sinal negativo no conjunto atual.",
      tone: negativeShare > 35 ? "negative" : "neutral",
    },
    {
      title: alertSector ? `${capitalize(alertSector)} em observacao` : "Sem setor critico",
      body: alertSector ? "Setor com menor termometro medio agora." : "Nenhum setor com viés negativo relevante.",
      tone: alertSector ? "negative" : "positive",
    },
    {
      title: "Top manchetes sensiveis",
      body: mostNegative.map((article) => article.title).join(" | ") || "Sem manchetes negativas no filtro.",
      tone: "neutral",
    },
  ];

  refs.alerts.innerHTML = alerts
    .map((alert) => `
      <div class="alert ${alert.tone}">
        <strong>${escapeHTML(alert.title)}</strong>
        <p>${escapeHTML(alert.body)}</p>
      </div>
    `)
    .join("");
}

function renderArticles(articles, total) {
  refs.articleCount.textContent = `${total} noticias no filtro atual`;
  refs.articles.innerHTML = articles
    .map((article) => {
      const sentimentClass = sentimentToClass(article.sentiment);
      return `
        <article class="article">
          <div class="article-head">
            <span class="source-name">${escapeHTML(article.source)}</span>
            <span class="score-chip">${article.score > 0 ? "+" : ""}${article.score}</span>
          </div>
          <h3>${escapeHTML(article.title)}</h3>
          <p>${escapeHTML(truncate(article.description || "Sem resumo disponivel.", 240))}</p>
          <div class="meta">
            <span class="pill ${sentimentClass}">${article.sentiment}</span>
            <span class="pill">${article.sector}</span>
            <span class="pill">${article.source}</span>
            <span class="pill">${formatDate(article.publishedAt)}</span>
            ${article.link ? `<a class="pill link" href="${escapeAttribute(article.link)}" target="_blank" rel="noreferrer">Abrir</a>` : ""}
          </div>
        </article>
      `;
    })
    .join("");
}

function pulseLabel(averageScore, risk) {
  if (risk >= 45) {
    return "Tenso";
  }
  if (averageScore > 0.35) {
    return "Otimista";
  }
  if (averageScore < -0.2) {
    return "Pressionado";
  }
  return "Estavel";
}

function dominantSentiment(counts) {
  return Object.entries(counts)
    .sort((a, b) => b[1] - a[1])[0]?.[0] || "-";
}

function filterArticles(articles) {
  const sector = refs.sectorFilter.value;
  const sentiment = refs.sentimentFilter.value;
  const query = refs.searchInput.value.trim().toLowerCase();

  return articles.filter((article) => {
    const matchesSector = sector === "all" || article.sector === sector;
    const matchesSentiment = sentiment === "all" || article.sentiment === sentiment;
    const haystack = `${article.title} ${article.description} ${article.source} ${article.entities?.join(" ") || ""}`.toLowerCase();
    const matchesQuery = !query || haystack.includes(query);
    return matchesSector && matchesSentiment && matchesQuery;
  });
}

function calculateRisk(summary) {
  if (!summary.totalArticles) {
    return 0;
  }
  const negative = summary.sentimentCounts.negativo || 0;
  const avgPenalty = Math.max(0, -summary.averageScore) * 12;
  return Math.min(100, Math.round((negative / summary.totalArticles) * 100 + avgPenalty));
}

function findAlertSector(sectors) {
  const sector = [...sectors].sort((a, b) => a.averageScore - b.averageScore)[0];
  if (!sector || sector.averageScore >= 0) {
    return "";
  }
  return sector.sector;
}

function countBy(items, key) {
  return items.reduce((acc, item) => {
    acc[item[key]] = (acc[item[key]] || 0) + 1;
    return acc;
  }, {});
}

function sentimentToClass(sentiment) {
  if (sentiment === "positivo") return "positive";
  if (sentiment === "negativo") return "negative";
  return "neutral";
}

function formatDate(value) {
  return new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(new Date(value));
}

function escapeHTML(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function escapeAttribute(value) {
  return escapeHTML(value).replaceAll("`", "&#096;");
}

function capitalize(value) {
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function truncate(value, limit) {
  const text = String(value).replace(/\s+/g, " ").trim();
  if (text.length <= limit) {
    return text;
  }
  return `${text.slice(0, limit - 1)}...`;
}

refs.refreshButton.addEventListener("click", async () => {
  refs.refreshButton.disabled = true;
  refs.refreshButton.textContent = "Coletando...";
  await refreshNews();
  await loadDashboard();
  refs.refreshButton.disabled = false;
  refs.refreshButton.textContent = "Atualizar RSS";
});

refs.sectorFilter.addEventListener("change", renderDashboard);
refs.sentimentFilter.addEventListener("change", renderDashboard);
refs.searchInput.addEventListener("input", renderDashboard);

loadDashboard();
