package main

import (
	"encoding/json"
	"log"
	"net/http"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"neondrift/backend/internal/leaderboard"
)

const defaultAddr = ":8090"

type gameConfig struct {
	WorldWidth      int     `json:"worldWidth"`
	WorldHeight     int     `json:"worldHeight"`
	PlayerRadius    float64 `json:"playerRadius"`
	BaseSpeed       float64 `json:"baseSpeed"`
	ObstacleCount   int     `json:"obstacleCount"`
	EnergyCount     int     `json:"energyCount"`
	DifficultyRamp  float64 `json:"difficultyRamp"`
	ScoreMultiplier float64 `json:"scoreMultiplier"`
}

type scoreRequest struct {
	Name     string  `json:"name"`
	Score    int     `json:"score"`
	Distance float64 `json:"distance"`
	Duration float64 `json:"duration"`
}

func main() {
	addr := os.Getenv("ADDR")
	if addr == "" {
		addr = defaultAddr
	}

	store := leaderboard.NewStore(10)
	mux := http.NewServeMux()

	mux.HandleFunc("GET /api/health", writeJSON(map[string]string{"status": "ok"}))
	mux.HandleFunc("GET /api/config", writeJSON(defaultConfig()))
	mux.HandleFunc("GET /api/leaderboard", func(w http.ResponseWriter, _ *http.Request) {
		respondJSON(w, http.StatusOK, store.Top())
	})
	mux.HandleFunc("POST /api/scores", func(w http.ResponseWriter, r *http.Request) {
		var input scoreRequest
		if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
			respondError(w, http.StatusBadRequest, "invalid json")
			return
		}

		name := sanitizeName(input.Name)
		if input.Score <= 0 || input.Duration <= 0 {
			respondError(w, http.StatusBadRequest, "invalid score")
			return
		}

		entry := store.Add(leaderboard.Entry{
			Name:      name,
			Score:     input.Score,
			Distance:  input.Distance,
			Duration:  input.Duration,
			CreatedAt: time.Now().UTC(),
		})
		respondJSON(w, http.StatusCreated, entry)
	})

	frontendDir := os.Getenv("FRONTEND_DIR")
	if frontendDir == "" {
		frontendDir = filepath.Clean("../frontend")
	}
	mux.Handle("/", http.FileServer(http.Dir(frontendDir)))

	log.Printf("Neon Drift listening on http://localhost%s", addr)
	if err := http.ListenAndServe(addr, withCORS(mux)); err != nil {
		log.Fatalf("server stopped: %v", err)
	}
}

func defaultConfig() gameConfig {
	return gameConfig{
		WorldWidth:      2200,
		WorldHeight:     1600,
		PlayerRadius:    14,
		BaseSpeed:       260,
		ObstacleCount:   34,
		EnergyCount:     28,
		DifficultyRamp:  0.055,
		ScoreMultiplier: 10,
	}
}

func sanitizeName(name string) string {
	name = strings.TrimSpace(name)
	if name == "" {
		return "Pilot"
	}
	if len(name) > 18 {
		return name[:18]
	}
	return name
}

func writeJSON(payload any) http.HandlerFunc {
	return func(w http.ResponseWriter, _ *http.Request) {
		respondJSON(w, http.StatusOK, payload)
	}
}

func respondJSON(w http.ResponseWriter, status int, payload any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	if err := json.NewEncoder(w).Encode(payload); err != nil {
		log.Printf("json response failed: %v", err)
	}
}

func respondError(w http.ResponseWriter, status int, message string) {
	respondJSON(w, status, map[string]string{"error": message, "status": strconv.Itoa(status)})
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
