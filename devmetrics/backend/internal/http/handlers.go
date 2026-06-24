package http

import (
	"encoding/json"
	"errors"
	"log"
	"net/http"
	"strings"
	"sync"
	"time"

	"devmetrics/backend/internal/ai"
	"devmetrics/backend/internal/cache"
	githubclient "devmetrics/backend/internal/github"
	"devmetrics/backend/internal/metrics"
	"github.com/go-chi/chi/v5"
)

type cachedUserData struct {
	user     *githubclient.User
	repos    []githubclient.Repository
	langData map[string]int
}

type Handlers struct {
	github    *githubclient.Client
	analyzer  *metrics.Analyzer
	insights  *ai.InsightsService
	userCache *cache.Cache
	contCache *cache.Cache
}

func NewHandlers(gh *githubclient.Client, analyzer *metrics.Analyzer, ins *ai.InsightsService) *Handlers {
	return &Handlers{
		github:    gh,
		analyzer:  analyzer,
		insights:  ins,
		userCache: cache.New(5 * time.Minute),
		contCache: cache.New(10 * time.Minute),
	}
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
	key := strings.ToLower(username)
	if cached, ok := h.userCache.Get(key); ok {
		d := cached.(*cachedUserData)
		return d.user, d.repos, d.langData, nil
	}

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

	// Fetch languages from top-starred repos for representative results
	topRepos := githubclient.TopReposByStars(repos, 30)
	var langMaps []map[string]int
	var langMu sync.Mutex
	var langWg sync.WaitGroup
	sem := make(chan struct{}, 10) // max 10 concurrent language requests
	for _, repo := range topRepos {
		langWg.Add(1)
		go func(r githubclient.Repository) {
			defer langWg.Done()
			sem <- struct{}{}
			defer func() { <-sem }()
			lm, err := h.github.GetRepoLanguages(username, r.Name)
			if err != nil {
				log.Printf("languages %s: %v", r.Name, err)
				return
			}
			langMu.Lock()
			langMaps = append(langMaps, lm)
			langMu.Unlock()
		}(repo)
	}
	langWg.Wait()

	aggregated := metrics.AggregateLanguages(langMaps)

	d := &cachedUserData{user: user, repos: repos, langData: aggregated}
	h.userCache.Set(key, d)
	return user, repos, aggregated, nil
}

type userMetricsResponse struct {
	User    *githubclient.User `json:"user"`
	Metrics *metrics.Metrics   `json:"metrics"`
}

func (h *Handlers) githubErrStatus(err error) int {
	if errors.Is(err, githubclient.ErrNotFound) {
		return http.StatusNotFound
	}
	if errors.Is(err, githubclient.ErrRateLimit) {
		return http.StatusTooManyRequests
	}
	return http.StatusBadGateway
}

func (h *Handlers) GetUserMetrics(w http.ResponseWriter, r *http.Request) {
	username := chi.URLParam(r, "username")
	if username == "" {
		writeError(w, http.StatusBadRequest, "username é obrigatório")
		return
	}
	user, repos, langData, err := h.fetchUserData(username)
	if err != nil {
		writeError(w, h.githubErrStatus(err), err.Error())
		return
	}
	m := h.analyzer.Compute(repos, langData)
	writeJSON(w, http.StatusOK, userMetricsResponse{User: user, Metrics: m})
}

func (h *Handlers) GetLanguages(w http.ResponseWriter, r *http.Request) {
	username := chi.URLParam(r, "username")
	if username == "" {
		writeError(w, http.StatusBadRequest, "username é obrigatório")
		return
	}
	_, repos, langData, err := h.fetchUserData(username)
	if err != nil {
		writeError(w, h.githubErrStatus(err), err.Error())
		return
	}
	m := h.analyzer.Compute(repos, langData)
	writeJSON(w, http.StatusOK, map[string]interface{}{"languages": m.Languages})
}

func (h *Handlers) GetInsights(w http.ResponseWriter, r *http.Request) {
	username := chi.URLParam(r, "username")
	if username == "" {
		writeError(w, http.StatusBadRequest, "username é obrigatório")
		return
	}
	_, repos, langData, err := h.fetchUserData(username)
	if err != nil {
		writeError(w, h.githubErrStatus(err), err.Error())
		return
	}
	m := h.analyzer.Compute(repos, langData)
	keyOverride := r.Header.Get("X-Mistral-Key")
	insights, err := h.insights.GenerateInsightsWithKey(username, m, keyOverride)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusOK, map[string]interface{}{"insights": insights})
}

func (h *Handlers) GetContributions(w http.ResponseWriter, r *http.Request) {
	username := chi.URLParam(r, "username")
	if username == "" {
		writeError(w, http.StatusBadRequest, "username é obrigatório")
		return
	}

	key := strings.ToLower(username)
	if cached, ok := h.contCache.Get(key); ok {
		writeJSON(w, http.StatusOK, cached)
		return
	}

	cal, err := h.github.GetContributions(username)
	if errors.Is(err, githubclient.ErrNoToken) {
		writeJSON(w, http.StatusOK, map[string]interface{}{
			"total_contributions": 0,
			"weeks":               []interface{}{},
			"error":               "GITHUB_TOKEN necessário para acessar dados de contribuição",
		})
		return
	}
	if err != nil {
		writeError(w, http.StatusBadGateway, err.Error())
		return
	}

	result := map[string]interface{}{
		"total_contributions": cal.TotalContributions,
		"weeks":               cal.Weeks,
	}
	h.contCache.Set(key, result)
	writeJSON(w, http.StatusOK, result)
}
