package main

import (
	"fmt"
	"log"
	"net/http"

	"github.com/go-chi/chi/v5"
	"github.com/go-chi/chi/v5/middleware"
	"github.com/go-chi/cors"
	"github.com/tassiosales/memmap/internal/config"
	"github.com/tassiosales/memmap/internal/handlers"
	"github.com/tassiosales/memmap/internal/repository"
	"github.com/tassiosales/memmap/internal/server"
)

func main() {
	cfg := config.Load()

	// Open database
	repo, err := repository.New(cfg.DBPath)
	if err != nil {
		log.Fatalf("open repository: %v", err)
	}
	defer repo.Close()

	// WebSocket hub
	hub := server.NewHub()
	go hub.Run()

	// HTTP handlers
	h := handlers.New(repo, hub)

	// Router
	r := chi.NewRouter()
	r.Use(middleware.Logger)
	r.Use(middleware.Recoverer)
	r.Use(cors.Handler(cors.Options{
		AllowedOrigins:   []string{"*"},
		AllowedMethods:   []string{"GET", "POST", "DELETE", "OPTIONS"},
		AllowedHeaders:   []string{"Accept", "Authorization", "Content-Type"},
		AllowCredentials: false,
		MaxAge:           300,
	}))

	r.Get("/notes", h.ListNotes)
	r.Post("/notes", h.CreateNote)
	r.Get("/notes/{id}", h.GetNote)
	r.Delete("/notes/{id}", h.DeleteNote)
	r.Get("/graph", h.GetGraph)
	r.Get("/ws", h.HandleWS)

	addr := fmt.Sprintf(":%s", cfg.APIPort)
	log.Printf("MemMap API listening on %s (DB: %s, NLP: %s)", addr, cfg.DBPath, cfg.NLPServiceURL)
	if err := http.ListenAndServe(addr, r); err != nil {
		log.Fatalf("server: %v", err)
	}
}
