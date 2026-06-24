package main

import (
	"fmt"
	"log"
	"net/http"
	"os"

	"devmetrics/backend/internal/ai"
	githubclient "devmetrics/backend/internal/github"
	internalhttp "devmetrics/backend/internal/http"
	"devmetrics/backend/internal/metrics"
	"github.com/joho/godotenv"
)

func main() {
	// Tenta carregar .env da raiz do projeto (devmetrics/.env)
	if err := godotenv.Load("../.env"); err != nil {
		godotenv.Load(".env")
	}

	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}
	githubToken := os.Getenv("GITHUB_TOKEN")
	mistralKey := os.Getenv("MISTRAL_API_KEY")

	ghClient := githubclient.NewClient(githubToken)
	analyzer := metrics.NewAnalyzer()
	insightsService := ai.NewInsightsService(mistralKey)

	handlers := internalhttp.NewHandlers(ghClient, analyzer, insightsService)
	router := internalhttp.NewRouter(handlers)

	addr := fmt.Sprintf(":%s", port)
	log.Printf("DevMetrics backend starting on %s", addr)
	if err := http.ListenAndServe(addr, router); err != nil {
		log.Fatal(err)
	}
}
