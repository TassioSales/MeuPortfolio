package http

import (
	"encoding/json"
	"log"
	"net/http"
	"sync"

	"devmetrics/backend/internal/ai"
	githubclient "devmetrics/backend/internal/github"
	"devmetrics/backend/internal/metrics"
	"github.com/go-chi/chi/v5"
)

type Handlers struct {
	github   *githubclient.Client
	analyzer *metrics.Analyzer
	insights *ai.InsightsService
}

func NewHandlers(gh *githubclient.Client, analyzer *metrics.Analyzer, ins *ai.InsightsService) *Handlers {
	return &Handlers{github: gh, analyzer: analyzer, insights: ins}
}

func writeJSON(w http.ResponseWriter, status int, v interface{}) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(v)
}

func writeError(w http.ResponseWriter, status int, msg string) {
	writeJSON(w, status, map[string]string{"error": msg})
}

func (h *Handlers) Health(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func (h *Handlers) fetchUserData(username string) (*githubclient.User, []githubclient.Repository, map[string]int, error) {
	var (
		user    *githubclient.User
		repos   []githubclient.Repository
		userErr error
		repoErr error
		wg      sync.WaitGroup
	)

	wg.Add(2)
	go func() {
		defer wg.Done()
		user, userErr = h.github.GetUser(username)
	}()
	go func() {
		defer wg.Done()
		repos, repoErr = h.github.GetRepos(username)
	}()
	wg.Wait()

	if userErr != nil {
		return nil, nil, nil, userErr
	}
	if repoErr != nil {
		return nil, nil, nil, repoErr
	}

	// Aggregate languages from top repos (limit to avoid rate limiting)
	var langMaps []map[string]int
	limit := len(repos)
	if limit > 20 {
		limit = 20
	}
	var langMu sync.Mutex
	var langWg sync.WaitGroup
	for _, repo := range repos[:limit] {
		langWg.Add(1)
		go func(r githubclient.Repository) {
			defer langWg.Done()
			lm, err := h.github.GetRepoLanguages(username, r.Name)
			if err != nil {
				log.Printf("failed to get languages for %s: %v", r.Name, err)
				return
			}
			langMu.Lock()
			langMaps = append(langMaps, lm)
			langMu.Unlock()
		}(repo)
	}
	langWg.Wait()

	aggregated := metrics.AggregateLanguages(langMaps)
	return user, repos, aggregated, nil
}

type userMetricsResponse struct {
	User    *githubclient.User `json:"user"`
	Metrics *metrics.Metrics   `json:"metrics"`
}

func (h *Handlers) GetUserMetrics(w http.ResponseWriter, r *http.Request) {
	username := chi.URLParam(r, "username")
	if username == "" {
		writeError(w, http.StatusBadRequest, "username is required")
		return
	}

	user, repos, langData, err := h.fetchUserData(username)
	if err != nil {
		writeError(w, http.StatusBadGateway, err.Error())
		return
	}

	m := h.analyzer.Compute(repos, langData)
	writeJSON(w, http.StatusOK, userMetricsResponse{User: user, Metrics: m})
}

func (h *Handlers) GetLanguages(w http.ResponseWriter, r *http.Request) {
	username := chi.URLParam(r, "username")
	if username == "" {
		writeError(w, http.StatusBadRequest, "username is required")
		return
	}

	_, repos, langData, err := h.fetchUserData(username)
	if err != nil {
		writeError(w, http.StatusBadGateway, err.Error())
		return
	}

	m := h.analyzer.Compute(repos, langData)
	writeJSON(w, http.StatusOK, map[string]interface{}{"languages": m.Languages})
}

func (h *Handlers) GetInsights(w http.ResponseWriter, r *http.Request) {
	username := chi.URLParam(r, "username")
	if username == "" {
		writeError(w, http.StatusBadRequest, "username is required")
		return
	}

	_, repos, langData, err := h.fetchUserData(username)
	if err != nil {
		writeError(w, http.StatusBadGateway, err.Error())
		return
	}

	m := h.analyzer.Compute(repos, langData)
	insights, err := h.insights.GenerateInsights(username, m)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusOK, map[string]interface{}{"insights": insights})
}
