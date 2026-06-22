package config

import "os"

type Config struct {
	Port   string
	DBPath string
}

func Load() Config {
	port := os.Getenv("API_PORT")
	if port == "" {
		port = "8080"
	}
	dbPath := os.Getenv("DB_PATH")
	if dbPath == "" {
		dbPath = "../../data/panorama.db"
	}
	return Config{Port: port, DBPath: dbPath}
}
