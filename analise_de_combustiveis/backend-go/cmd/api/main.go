package main

import (
	"log"
	"net/http"
	"os"

	"fuel-analytics-api/internal/config"
	"fuel-analytics-api/internal/domain"
	apphttp "fuel-analytics-api/internal/http"
	"fuel-analytics-api/internal/repository"
	"fuel-analytics-api/internal/service"
)

func main() {
	log.SetOutput(os.Stdout)
	cfg := config.Load()

	var repo domain.Repository
	var err error

	if _, err := os.Stat(cfg.DuckDBPath); err == nil {
		log.Printf("using DuckDB repository: %s", cfg.DuckDBPath)
		repo, err = repository.NewDuckDBRepository(cfg.DuckDBPath)
		if err != nil {
			log.Printf("duckdb unavailable, falling back to snapshot repository. Detail: %v", err)
			repo, err = repository.NewAnalyticsRepository(
				cfg.OverviewPath,
				cfg.HistoryPath,
				cfg.FuelsPath,
				cfg.ExplorerPath,
				cfg.ForecastPath,
				cfg.MarketPath,
			)
		}
	} else {
		log.Printf("duckdb not found, using legacy snapshot repository. Detail: %v", err)
		repo, err = repository.NewAnalyticsRepository(
			cfg.OverviewPath,
			cfg.HistoryPath,
			cfg.FuelsPath,
			cfg.ExplorerPath,
			cfg.ForecastPath,
			cfg.MarketPath,
		)
	}

	if err != nil {
		log.Fatalf("repository init failed: %v", err)
	}

	insights := service.NewInsightsService(cfg.MistralAPIKey, cfg.MistralModel)
	router := apphttp.NewRouter(repo, insights)

	log.Printf("fuel analytics api listening on :%s", cfg.Port)
	if err := http.ListenAndServe(":"+cfg.Port, router); err != nil {
		log.Fatalf("server failed: %v", err)
	}
}
