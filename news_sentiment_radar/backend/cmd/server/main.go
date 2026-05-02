package main

import (
	"context"
	"encoding/json"
	"log"
	"net/http"
	"os"
	"path/filepath"
	"time"

	"newssentiment/backend/internal/news"
)

const defaultAddr = ":8092"

func main() {
	addr := os.Getenv("ADDR")
	if addr == "" {
		addr = defaultAddr
	}

	store := news.NewStore(defaultSources())
	go func() {
		ctx, cancel := context.WithTimeout(context.Background(), 12*time.Second)
		defer cancel()
		count := store.Refresh(ctx)
		log.Printf("initial news refresh collected %d articles", count)
	}()

	mux := http.NewServeMux()
	mux.HandleFunc("GET /api/health", func(w http.ResponseWriter, _ *http.Request) {
		respondJSON(w, http.StatusOK, map[string]string{"status": "ok"})
	})
	mux.HandleFunc("GET /api/sources", func(w http.ResponseWriter, _ *http.Request) {
		respondJSON(w, http.StatusOK, store.Sources())
	})
	mux.HandleFunc("GET /api/articles", func(w http.ResponseWriter, _ *http.Request) {
		respondJSON(w, http.StatusOK, store.Articles())
	})
	mux.HandleFunc("GET /api/summary", func(w http.ResponseWriter, _ *http.Request) {
		respondJSON(w, http.StatusOK, store.Summary())
	})
	mux.HandleFunc("POST /api/refresh", func(w http.ResponseWriter, _ *http.Request) {
		ctx, cancel := context.WithTimeout(context.Background(), 15*time.Second)
		defer cancel()
		count := store.Refresh(ctx)
		respondJSON(w, http.StatusOK, map[string]any{"articles": count, "summary": store.Summary()})
	})

	frontendDir := os.Getenv("FRONTEND_DIR")
	if frontendDir == "" {
		frontendDir = filepath.Clean("../frontend")
	}
	mux.Handle("/", http.FileServer(http.Dir(frontendDir)))

	log.Printf("News Sentiment Radar listening on http://localhost%s", addr)
	if err := http.ListenAndServe(addr, withCORS(mux)); err != nil {
		log.Fatalf("server stopped: %v", err)
	}
}

func defaultSources() []news.Source {
	return []news.Source{
		{Name: "G1", URL: "https://g1.globo.com/rss/g1/", Sector: "geral"},
		{Name: "BBC Brasil", URL: "https://feeds.bbci.co.uk/portuguese/rss.xml", Sector: "geral"},
		{Name: "Tecnoblog", URL: "https://tecnoblog.net/feed/", Sector: "tecnologia"},
		{Name: "Poder360", URL: "https://www.poder360.com.br/feed/", Sector: "politica"},
	}
}

func respondJSON(w http.ResponseWriter, status int, payload any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	if err := json.NewEncoder(w).Encode(payload); err != nil {
		log.Printf("json response failed: %v", err)
	}
}

func withCORS(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Access-Control-Allow-Origin", "*")
		w.Header().Set("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
		w.Header().Set("Access-Control-Allow-Headers", "Content-Type")
		if r.Method == http.MethodOptions {
			w.WriteHeader(http.StatusNoContent)
			return
		}
		next.ServeHTTP(w, r)
	})
}
