package main

import (
	"log"

	"github.com/tassiosales/panorama_br/internal/config"
	"github.com/tassiosales/panorama_br/internal/server"
)

func main() {
	cfg := config.Load()
	log.Printf("Iniciando Panorama BR API | porta=%s db=%s", cfg.Port, cfg.DBPath)
	if err := server.Run(cfg.Port, cfg.DBPath); err != nil {
		log.Fatal(err)
	}
}
