package main

import (
	"fmt"
	"log"
	"net/http"
	"os"

	"encurtador_url/backend/internal/analytics"
	handler "encurtador_url/backend/internal/http"
	"encurtador_url/backend/internal/shortener"
	"encurtador_url/backend/internal/storage"
)

func main() {
	db, err := storage.Open()
	if err != nil {
		log.Fatalf("failed to open database: %v", err)
	}
	defer db.Close()

	svc := shortener.New(db)
	tracker := analytics.New(db)
	h := handler.New(db, svc, tracker)
	router := handler.NewRouter(h)

	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	addr := fmt.Sprintf(":%s", port)
	log.Printf("encurtador_url API listening on %s", addr)
	if err := http.ListenAndServe(addr, router); err != nil {
		log.Fatalf("server error: %v", err)
	}
}
