package server

import (
	"log"
	"net/http"

	"github.com/go-chi/chi/v5"
	"github.com/go-chi/chi/v5/middleware"
	"github.com/go-chi/cors"
	"github.com/tassiosales/panorama_br/internal/handlers"
	"github.com/tassiosales/panorama_br/internal/repository"
)

// Run inicializa o servidor HTTP com todas as rotas configuradas
func Run(port, dbPath string) error {
	repo, err := repository.New(dbPath)
	if err != nil {
		log.Printf("DB não encontrado em %s — iniciando sem dados: %v", dbPath, err)
		// Continua com repo nil — handlers tratam nil repo retornando dados vazios
	}
	if repo != nil {
		defer repo.Close()
	}

	h := handlers.New(repo)

	r := chi.NewRouter()
	r.Use(middleware.Logger)
	r.Use(middleware.Recoverer)
	r.Use(cors.Handler(cors.Options{
		AllowedOrigins: []string{"*"},
		AllowedMethods: []string{"GET", "OPTIONS"},
		AllowedHeaders: []string{"Accept", "Content-Type"},
	}))

	r.Get("/health", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.Write([]byte(`{"status":"ok"}`))
	})

	r.Route("/api/v1", func(r chi.Router) {
		r.Get("/macro", h.GetMacro)
		r.Get("/history/{indicator}", h.GetHistory)
		r.Get("/market", h.GetMarket)
		r.Get("/regional", h.GetRegional)
		r.Get("/status", h.GetStatus)
	})

	log.Printf("API rodando em :%s", port)
	return http.ListenAndServe(":"+port, r)
}
