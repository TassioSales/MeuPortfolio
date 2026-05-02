package config

import (
	"bufio"
	"os"
	"path/filepath"
	"strings"
)

type Config struct {
	Addr         string
	MistralKey   string
	MistralModel string
	StorageDir   string
	FrontendDir  string
}

func Load() Config {
	loadEnv(filepath.Clean("../.env"))
	addr := getenv("ADDR", ":8093")
	return Config{
		Addr:         addr,
		MistralKey:   os.Getenv("MISTRAL_API_KEY"),
		MistralModel: getenv("MISTRAL_MODEL", "mistral-small-latest"),
		StorageDir:   filepath.Clean("../storage"),
		FrontendDir:  filepath.Clean("../frontend"),
	}
}

func loadEnv(path string) {
	file, err := os.Open(path)
	if err != nil {
		return
	}
	defer file.Close()

	scanner := bufio.NewScanner(file)
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if line == "" || strings.HasPrefix(line, "#") || !strings.Contains(line, "=") {
			continue
		}
		parts := strings.SplitN(line, "=", 2)
		key := strings.TrimSpace(parts[0])
		value := strings.Trim(strings.TrimSpace(parts[1]), `"`)
		if os.Getenv(key) == "" {
			_ = os.Setenv(key, value)
		}
	}
}

func getenv(key, fallback string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return fallback
}
