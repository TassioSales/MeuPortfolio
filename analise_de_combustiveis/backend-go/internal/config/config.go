package config

import (
	"log"
	"os"
	"path/filepath"

	"github.com/joho/godotenv"
)

type Config struct {
	Port          string
	OverviewPath  string
	HistoryPath   string
	FuelsPath     string
	ExplorerPath  string
	ForecastPath  string
	MarketPath    string
	DuckDBPath    string
	MistralAPIKey string
	MistralModel  string
}

func Load() Config {
	_ = godotenv.Load(filepath.Join("..", ".env"))
	_ = godotenv.Load(filepath.Join("..", ".env.local"))
	_ = godotenv.Load(filepath.Join("..", ".env.local.example"))

	cfg := Config{
		Port:          envOrDefault("PORT", "8080"),
		OverviewPath:  envOrDefault("OVERVIEW_PATH", filepath.Join("..", "models", "overview.json")),
		HistoryPath:   envOrDefault("HISTORY_PATH", filepath.Join("..", "models", "history.json")),
		FuelsPath:     envOrDefault("FUELS_PATH", filepath.Join("..", "models", "fuels.json")),
		ExplorerPath:  envOrDefault("EXPLORER_PATH", filepath.Join("..", "models", "explorer.json")),
		ForecastPath:  envOrDefault("FORECAST_PATH", filepath.Join("..", "models", "forecasts.json")),
		MarketPath:    envOrDefault("MARKET_PATH", filepath.Join("..", "models", "market_signals.json")),
		DuckDBPath:    envOrDefault("DUCKDB_PATH", filepath.Join("..", "data-lake", "warehouse", "fuel_analytics.duckdb")),
		MistralAPIKey: os.Getenv("MISTRAL_API_KEY"),
		MistralModel:  envOrDefault("MISTRAL_MODEL", "mistral-small-latest"),
	}
	log.Printf(
		"overview=%s history=%s fuels=%s explorer=%s forecast=%s market=%s db=%s",
		cfg.OverviewPath,
		cfg.HistoryPath,
		cfg.FuelsPath,
		cfg.ExplorerPath,
		cfg.ForecastPath,
		cfg.MarketPath,
		cfg.DuckDBPath,
	)
	return cfg
}

func envOrDefault(name, fallback string) string {
	if value := os.Getenv(name); value != "" {
		return value
	}
	return fallback
}
