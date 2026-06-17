package handler

import (
	"net/http"

	"github.com/go-chi/chi/v5"
	"github.com/go-chi/chi/v5/middleware"
)

// NewRouter wires all routes and returns a ready-to-serve http.Handler.
func NewRouter(h *Handlers) http.Handler {
	r := chi.NewRouter()

	r.Use(middleware.Logger)
	r.Use(middleware.Recoverer)
	r.Use(corsMiddleware)

	// Redirect endpoint
	r.Get("/r/{code}", h.Redirect)

	// API routes
	r.Route("/api", func(r chi.Router) {
		r.Get("/health", h.Health)
		r.Post("/shorten", h.Shorten)
		r.Get("/urls", h.ListURLs)
		r.Get("/urls/{code}/stats", h.URLStats)
	})

	return r
}

// corsMiddleware adds permissive CORS headers for local dev.
func corsMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Access-Control-Allow-Origin", "*")
		w.Header().Set("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
		w.Header().Set("Access-Control-Allow-Headers", "Content-Type, Authorization")
		if r.Method == http.MethodOptions {
			w.WriteHeader(http.StatusNoContent)
			return
		}
		next.ServeHTTP(w, r)
	})
}
