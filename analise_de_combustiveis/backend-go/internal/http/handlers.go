package http

import (
	"encoding/json"
	"fmt"
	nethttp "net/http"

	"fuel-analytics-api/internal/domain"
	"fuel-analytics-api/internal/service"
	"log"
)

type Handler struct {
	repo         domain.Repository
	insights     *service.InsightsService
	mistralModel string
}

func (h *Handler) Health(w nethttp.ResponseWriter, r *nethttp.Request) {
	if err := h.repo.Health(r.Context()); err != nil {
		writeJSON(w, nethttp.StatusServiceUnavailable, map[string]any{"status": "down", "error": err.Error()})
		return
	}
	writeJSON(w, nethttp.StatusOK, map[string]any{"status": "ok"})
}

func (h *Handler) Fuels(w nethttp.ResponseWriter, r *nethttp.Request) {
	items, err := h.repo.Fuels(r.Context())
	if err != nil {
		writeError(w, err)
		return
	}
	writeJSON(w, nethttp.StatusOK, map[string]any{"data": items})
}

func (h *Handler) Overview(w nethttp.ResponseWriter, r *nethttp.Request) {
	fuel := r.URL.Query().Get("fuel")
	state := r.URL.Query().Get("state")
	startDate := r.URL.Query().Get("start_date")
	endDate := r.URL.Query().Get("end_date")
	items, err := h.repo.Overview(r.Context(), fuel, state, startDate, endDate)
	if err != nil {
		writeError(w, err)
		return
	}
	writeJSON(w, nethttp.StatusOK, map[string]any{"data": items})
}

func (h *Handler) History(w nethttp.ResponseWriter, r *nethttp.Request) {
	fuel := r.URL.Query().Get("fuel")
	state := r.URL.Query().Get("state")
	city := r.URL.Query().Get("city")
	startDate := r.URL.Query().Get("start_date")
	endDate := r.URL.Query().Get("end_date")
	items, err := h.repo.History(r.Context(), fuel, state, city, startDate, endDate)
	if err != nil {
		writeError(w, err)
		return
	}
	writeJSON(w, nethttp.StatusOK, map[string]any{"data": items})
}

func (h *Handler) Cities(w nethttp.ResponseWriter, r *nethttp.Request) {
	items, err := h.repo.Cities(r.Context(), r.URL.Query().Get("fuel"), r.URL.Query().Get("state"))
	if err != nil {
		writeError(w, err)
		return
	}
	writeJSON(w, nethttp.StatusOK, map[string]any{"data": items})
}

func (h *Handler) Forecast(w nethttp.ResponseWriter, r *nethttp.Request) {
	fuel := r.URL.Query().Get("fuel")
	state := r.URL.Query().Get("state")
	startDate := r.URL.Query().Get("start_date")
	endDate := r.URL.Query().Get("end_date")
	items, err := h.repo.Forecast(r.Context(), fuel, state, startDate, endDate)
	if err != nil {
		writeError(w, err)
		return
	}
	writeJSON(w, nethttp.StatusOK, map[string]any{"data": items})
}

func (h *Handler) Compare(w nethttp.ResponseWriter, r *nethttp.Request) {
	items, err := h.repo.Compare(
		r.Context(),
		r.URL.Query().Get("fuel"),
		r.URL.Query().Get("compare_with"),
		r.URL.Query().Get("state"),
		r.URL.Query().Get("start_date"),
		r.URL.Query().Get("end_date"),
	)
	if err != nil {
		writeError(w, err)
		return
	}
	writeJSON(w, nethttp.StatusOK, map[string]any{"data": items})
}

func (h *Handler) Map(w nethttp.ResponseWriter, r *nethttp.Request) {
	items, err := h.repo.Map(r.Context(), r.URL.Query().Get("fuel"))
	if err != nil {
		writeError(w, err)
		return
	}
	writeJSON(w, nethttp.StatusOK, map[string]any{"data": items})
}

func (h *Handler) Market(w nethttp.ResponseWriter, r *nethttp.Request) {
	fuel := r.URL.Query().Get("fuel")
	state := r.URL.Query().Get("state")
	startDate := r.URL.Query().Get("start_date")
	endDate := r.URL.Query().Get("end_date")
	items, err := h.repo.Market(r.Context(), fuel, state, startDate, endDate)
	if err != nil {
		writeError(w, err)
		return
	}
	writeJSON(w, nethttp.StatusOK, map[string]any{"data": items})
}

func (h *Handler) Explorer(w nethttp.ResponseWriter, r *nethttp.Request) {
	item, err := h.repo.Explorer(r.Context())
	if err != nil {
		writeError(w, err)
		return
	}
	writeJSON(w, nethttp.StatusOK, map[string]any{"data": item})
}

func (h *Handler) Insights(w nethttp.ResponseWriter, r *nethttp.Request) {
	fuel := r.URL.Query().Get("fuel")
	state := r.URL.Query().Get("state")
	view := r.URL.Query().Get("view")
	city := r.URL.Query().Get("city")
	startDate := r.URL.Query().Get("start_date")
	endDate := r.URL.Query().Get("end_date")
	compareWith := r.URL.Query().Get("compare_with")

	summaries, err := h.repo.Overview(r.Context(), fuel, state, startDate, endDate)
	if err != nil {
		writeError(w, err)
		return
	}
	history, err := h.repo.History(r.Context(), fuel, state, city, startDate, endDate)
	if err != nil {
		writeError(w, err)
		return
	}
	forecast, err := h.repo.Forecast(r.Context(), fuel, state, startDate, endDate)
	if err != nil {
		writeError(w, err)
		return
	}
	market, err := h.repo.Market(r.Context(), fuel, state, startDate, endDate)
	if err != nil {
		writeError(w, err)
		return
	}
	comparison := []domain.ComparisonPoint{}
	if compareWith != "" {
		comparison, _ = h.repo.Compare(r.Context(), fuel, compareWith, state, startDate, endDate)
	}
	svc := h.insights
	if headerKey := r.Header.Get("X-Mistral-Key"); headerKey != "" {
		svc = service.NewInsightsService(headerKey, h.mistralModel)
	}
	item, err := svc.Build(r.Context(), service.InsightContext{
		View:        view,
		Fuel:        fuel,
		State:       state,
		City:        city,
		CompareWith: compareWith,
		StartDate:   startDate,
		EndDate:     endDate,
		Overview:    summaries,
		History:     history,
		Forecast:    forecast,
		Comparison:  comparison,
		Market:      market,
	})
	if err != nil {
		writeError(w, err)
		return
	}
	writeJSON(w, nethttp.StatusOK, map[string]any{"data": item})
}

func (h *Handler) Ranking(w nethttp.ResponseWriter, r *nethttp.Request) {
	ext, ok := h.repo.(domain.ExtendedRepository)
	if !ok {
		writeJSON(w, nethttp.StatusNotImplemented, map[string]any{"error": "not supported by current repository"})
		return
	}
	fuel := r.URL.Query().Get("fuel")
	order := r.URL.Query().Get("order")
	if order == "" {
		order = "desc"
	}
	limit := 0
	if ls := r.URL.Query().Get("limit"); ls != "" {
		if _, err := fmt.Sscanf(ls, "%d", &limit); err != nil {
			limit = 0
		}
	}
	items, err := ext.Ranking(r.Context(), fuel, order, limit)
	if err != nil {
		writeError(w, err)
		return
	}
	writeJSON(w, nethttp.StatusOK, map[string]any{"data": items})
}

func (h *Handler) Trends(w nethttp.ResponseWriter, r *nethttp.Request) {
	ext, ok := h.repo.(domain.ExtendedRepository)
	if !ok {
		writeJSON(w, nethttp.StatusNotImplemented, map[string]any{"error": "not supported by current repository"})
		return
	}
	items, err := ext.Trends(
		r.Context(),
		r.URL.Query().Get("fuel"),
		r.URL.Query().Get("state"),
		r.URL.Query().Get("start_date"),
		r.URL.Query().Get("end_date"),
	)
	if err != nil {
		writeError(w, err)
		return
	}
	writeJSON(w, nethttp.StatusOK, map[string]any{"data": items})
}

func (h *Handler) Stats(w nethttp.ResponseWriter, r *nethttp.Request) {
	ext, ok := h.repo.(domain.ExtendedRepository)
	if !ok {
		writeJSON(w, nethttp.StatusNotImplemented, map[string]any{"error": "not supported by current repository"})
		return
	}
	item, err := ext.Stats(
		r.Context(),
		r.URL.Query().Get("fuel"),
		r.URL.Query().Get("start_date"),
		r.URL.Query().Get("end_date"),
	)
	if err != nil {
		writeError(w, err)
		return
	}
	writeJSON(w, nethttp.StatusOK, map[string]any{"data": item})
}

func writeJSON(w nethttp.ResponseWriter, status int, payload any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(payload)
}

func writeError(w nethttp.ResponseWriter, err error) {
	log.Printf("ERROR: %v", err)
	writeJSON(w, nethttp.StatusInternalServerError, map[string]any{"error": err.Error()})
}
