package handlers

import (
	"database/sql"
	"encoding/json"
	"net/http"
	"strconv"

	"github.com/go-chi/chi/v5"
	"github.com/tassiosales/panorama_br/internal/domain"
	"github.com/tassiosales/panorama_br/internal/repository"
)

// Handler agrupa o repositório e expõe os endpoints HTTP
type Handler struct {
	repo *repository.Repository
}

// New cria um novo Handler; repo pode ser nil se o DB não estiver disponível
func New(repo *repository.Repository) *Handler {
	return &Handler{repo: repo}
}

// writeJSON serializa v como JSON e envia com o status code fornecido
func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(v)
}

// noData retorna uma resposta padronizada quando não há dados disponíveis
func noData(w http.ResponseWriter) {
	writeJSON(w, http.StatusOK, map[string]string{
		"error":  "sem dados",
		"status": "no_data",
	})
}

// isNoData verifica se o erro indica ausência de dados (tabela vazia ou sem linhas)
func isNoData(err error) bool {
	return err == sql.ErrNoRows
}

// GetMacro — GET /api/v1/macro
// Retorna todos os indicadores macro com timestamp da atualização mais recente
func (h *Handler) GetMacro(w http.ResponseWriter, r *http.Request) {
	if h.repo == nil {
		noData(w)
		return
	}

	indicators, err := h.repo.GetMacroIndicators()
	if err != nil || len(indicators) == 0 {
		noData(w)
		return
	}

	lastUpdated := ""
	for _, ind := range indicators {
		if ind.UpdatedAt > lastUpdated {
			lastUpdated = ind.UpdatedAt
		}
	}

	writeJSON(w, http.StatusOK, domain.MacroResponse{
		Indicators:  indicators,
		LastUpdated: lastUpdated,
	})
}

// GetHistory — GET /api/v1/history/{indicator}?days=90
// Retorna série histórica de um indicador nos últimos N dias
func (h *Handler) GetHistory(w http.ResponseWriter, r *http.Request) {
	if h.repo == nil {
		noData(w)
		return
	}

	indicator := chi.URLParam(r, "indicator")

	days := 90
	if d := r.URL.Query().Get("days"); d != "" {
		if parsed, err := strconv.Atoi(d); err == nil && parsed > 0 {
			days = parsed
		}
	}

	points, err := h.repo.GetIndicatorHistory(indicator, days)
	if err != nil {
		noData(w)
		return
	}
	if points == nil {
		points = []domain.HistoryPoint{}
	}

	writeJSON(w, http.StatusOK, points)
}

// GetMarket — GET /api/v1/market
// Retorna snapshot do mercado separando Ibovespa dos demais ativos
func (h *Handler) GetMarket(w http.ResponseWriter, r *http.Request) {
	if h.repo == nil {
		noData(w)
		return
	}

	stocks, err := h.repo.GetMarketSnapshot()
	if err != nil || len(stocks) == 0 {
		noData(w)
		return
	}

	var ibovespa *domain.StockItem
	var others []domain.StockItem
	lastUpdated := ""

	for i, s := range stocks {
		if s.Symbol == "^BVSP" || s.Symbol == "BVSP" {
			ibovespa = &stocks[i]
		} else {
			others = append(others, s)
		}
		if s.UpdatedAt > lastUpdated {
			lastUpdated = s.UpdatedAt
		}
	}

	if others == nil {
		others = []domain.StockItem{}
	}

	writeJSON(w, http.StatusOK, domain.MarketResponse{
		Ibovespa:    ibovespa,
		Stocks:      others,
		LastUpdated: lastUpdated,
	})
}

// GetRegional — GET /api/v1/regional
// Retorna dados regionais por estado ordenados por PIB
func (h *Handler) GetRegional(w http.ResponseWriter, r *http.Request) {
	if h.repo == nil {
		noData(w)
		return
	}

	data, err := h.repo.GetRegionalData()
	if err != nil {
		noData(w)
		return
	}
	if data == nil {
		data = []domain.RegionalData{}
	}

	writeJSON(w, http.StatusOK, data)
}

// GetStatus — GET /api/v1/status
// Retorna estado geral da API e do pipeline
func (h *Handler) GetStatus(w http.ResponseWriter, r *http.Request) {
	if h.repo == nil {
		writeJSON(w, http.StatusOK, domain.StatusResponse{
			Status:          "sem_dados",
			PipelineLastRun: "",
			RecordsCount:    0,
			DBPath:          "",
		})
		return
	}

	lastRun, err := h.repo.GetLastPipelineRun()
	if isNoData(err) || err != nil {
		lastRun = ""
	}

	count, err := h.repo.GetRecordsCount()
	if err != nil {
		count = 0
	}

	status := "ok"
	if count == 0 {
		status = "sem_dados"
	}

	writeJSON(w, http.StatusOK, domain.StatusResponse{
		Status:          status,
		PipelineLastRun: lastRun,
		RecordsCount:    count,
		DBPath:          "",
	})
}
