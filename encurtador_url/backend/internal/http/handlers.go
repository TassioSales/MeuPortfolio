package handler

import (
	"encoding/json"
	"net/http"
	"os"

	"github.com/go-chi/chi/v5"

	"encurtador_url/backend/internal/analytics"
	"encurtador_url/backend/internal/shortener"
	"encurtador_url/backend/internal/storage"
)

// Handlers holds all HTTP handler dependencies.
type Handlers struct {
	db      *storage.DB
	svc     *shortener.Service
	tracker *analytics.Tracker
}

// New creates a Handlers instance.
func New(db *storage.DB, svc *shortener.Service, tracker *analytics.Tracker) *Handlers {
	return &Handlers{db: db, svc: svc, tracker: tracker}
}

func baseURL() string {
	if u := os.Getenv("BASE_URL"); u != "" {
		return u
	}
	return "http://localhost:8080"
}

// Health godoc
// GET /api/health
func (h *Handlers) Health(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

// Shorten godoc
// POST /api/shorten
func (h *Handlers) Shorten(w http.ResponseWriter, r *http.Request) {
	var body struct {
		URL string `json:"url"`
	}
	if err := json.NewDecoder(r.Body).Decode(&body); err != nil || body.URL == "" {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "invalid or missing 'url' field"})
		return
	}

	url, err := h.svc.Shorten(body.URL)
	if err != nil {
		writeJSON(w, http.StatusInternalServerError, map[string]string{"error": err.Error()})
		return
	}

	writeJSON(w, http.StatusCreated, map[string]string{
		"short_code":   url.ShortCode,
		"short_url":    baseURL() + "/r/" + url.ShortCode,
		"original_url": url.OriginalURL,
	})
}

// Redirect godoc
// GET /r/{code}
func (h *Handlers) Redirect(w http.ResponseWriter, r *http.Request) {
	code := chi.URLParam(r, "code")
	url, err := h.db.GetURLByCode(code, 0)
	if err != nil {
		http.NotFound(w, r)
		return
	}

	// Record click asynchronously so redirect is fast.
	go func() { _ = h.tracker.Record(url.ID, r) }()

	http.Redirect(w, r, url.OriginalURL, http.StatusFound)
}

// ListURLs godoc
// GET /api/urls
func (h *Handlers) ListURLs(w http.ResponseWriter, r *http.Request) {
	urls, err := h.db.ListURLs()
	if err != nil {
		writeJSON(w, http.StatusInternalServerError, map[string]string{"error": err.Error()})
		return
	}
	if urls == nil {
		urls = []storage.URL{}
	}
	writeJSON(w, http.StatusOK, urls)
}

// URLStats godoc
// GET /api/urls/{code}/stats
func (h *Handlers) URLStats(w http.ResponseWriter, r *http.Request) {
	code := chi.URLParam(r, "code")
	stats, err := h.db.GetDailyStats(code)
	if err != nil {
		writeJSON(w, http.StatusInternalServerError, map[string]string{"error": err.Error()})
		return
	}
	if stats == nil {
		stats = []storage.DailyStat{}
	}
	writeJSON(w, http.StatusOK, stats)
}

// writeJSON is a helper that marshals v as JSON and writes it to w.
func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(v)
}
