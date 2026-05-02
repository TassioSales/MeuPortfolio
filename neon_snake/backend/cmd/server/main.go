package main

import (
	"encoding/json"
	"log"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"time"

	"neonsnake/backend/internal/scores"
)

const defaultAddr = ":8091"

type config struct {
	GridSize     int `json:"gridSize"`
	InitialSpeed int `json:"initialSpeed"`
	MinSpeed     int `json:"minSpeed"`
	FoodScore    int `json:"foodScore"`
}

type scoreRequest struct {
	Name   string `json:"name"`
	Score  int    `json:"score"`
	Length int    `json:"length"`
}

func main() {
	addr := os.Getenv("ADDR")
	if addr == "" {
		addr = defaultAddr
	}

	store := scores.NewStore(10)
	mux := http.NewServeMux()
	mux.HandleFunc("GET /api/health", func(w http.ResponseWriter, _ *http.Request) {
		respondJSON(w, http.StatusOK, map[string]string{"status": "ok"})
	})
	mux.HandleFunc("GET /api/config", func(w http.ResponseWriter, _ *http.Request) {
		respondJSON(w, http.StatusOK, config{GridSize: 24, InitialSpeed: 130, MinSpeed: 62, FoodScore: 100})
	})
	mux.HandleFunc("GET /api/leaderboard", func(w http.ResponseWriter, _ *http.Request) {
		respondJSON(w, http.StatusOK, store.Top())
	})
	mux.HandleFunc("POST /api/scores", func(w http.ResponseWriter, r *http.Request) {
		var input scoreRequest
		if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
			respondJSON(w, http.StatusBadRequest, map[string]string{"error": "invalid json"})
			return
		}
		if input.Score <= 0 || input.Length <= 0 {
			respondJSON(w, http.StatusBadRequest, map[string]string{"error": "invalid score"})
			return
		}

		entry := store.Add(scores.Entry{
			Name:      sanitizeName(input.Name),
			Score:     input.Score,
			Length:    input.Length,
			CreatedAt: time.Now().UTC(),
		})
		respondJSON(w, http.StatusCreated, entry)
	})

	frontendDir := os.Getenv("FRONTEND_DIR")
	if frontendDir == "" {
		frontendDir = filepath.Clean("../frontend")
	}
	mux.Handle("/", http.FileServer(http.Dir(frontendDir)))

	log.Printf("Neon Snake listening on http://localhost%s", addr)
	if err := http.ListenAndServe(addr, withCORS(mux)); err != nil {
		log.Fatalf("server stopped: %v", err)
	}
}

func sanitizeName(name string) string {
	name = strings.TrimSpace(name)
	if name == "" {
		return "Snake"
	}
	if len(name) > 18 {
		return name[:18]
	}
	return name
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
