package config

import (
	"os"
)

// Config holds all runtime configuration for the API server.
type Config struct {
	// APIPort is the port the HTTP server will listen on.
	APIPort string

	// DBPath is the filesystem path to the SQLite database file.
	DBPath string

	// NLPServiceURL is the base URL of the Python NLP service.
	NLPServiceURL string
}

// Load reads configuration from environment variables, using sensible defaults.
func Load() *Config {
	return &Config{
		APIPort:       getEnv("API_PORT", "8080"),
		DBPath:        getEnv("DB_PATH", "./data/memmap.db"),
		NLPServiceURL: getEnv("NLP_URL", "http://localhost:8001"),
	}
}

func getEnv(key, defaultValue string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return defaultValue
}
