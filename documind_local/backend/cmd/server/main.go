package main

import (
	"context"
	"crypto/rand"
	"encoding/hex"
	"encoding/json"
	"io"
	"log"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"time"

	"documind/backend/internal/ai"
	"documind/backend/internal/config"
	"documind/backend/internal/domain"
	"documind/backend/internal/extract"
	"documind/backend/internal/store"
)

type server struct {
	cfg   config.Config
	store *store.Store
	ai    *ai.Client
}

func main() {
	cfg := config.Load()
	if err := os.MkdirAll(filepath.Join(cfg.StorageDir, "uploads"), 0o755); err != nil {
		log.Fatalf("storage init failed: %v", err)
	}

	documentStore, err := store.New(filepath.Join(cfg.StorageDir, "db.json"))
	if err != nil {
		log.Fatalf("store init failed: %v", err)
	}

	app := &server{
		cfg:   cfg,
		store: documentStore,
		ai:    ai.NewClient(cfg.MistralKey, cfg.MistralModel),
	}

	mux := http.NewServeMux()
	mux.HandleFunc("GET /api/health", app.health)
	mux.HandleFunc("GET /api/stats", app.stats)
	mux.HandleFunc("GET /api/documents", app.documents)
	mux.HandleFunc("POST /api/documents", app.upload)
	mux.HandleFunc("GET /api/search", app.search)
	mux.HandleFunc("GET /api/documents/", app.documentByID)
	mux.HandleFunc("POST /api/documents/", app.analyzeByID)
	mux.Handle("/", noCacheFileServer(cfg.FrontendDir))

	log.Printf("DocuMind Local listening on http://localhost%s", cfg.Addr)
	if err := http.ListenAndServe(cfg.Addr, withCORS(mux)); err != nil {
		log.Fatalf("server stopped: %v", err)
	}
}

func (s *server) health(w http.ResponseWriter, _ *http.Request) {
	respondJSON(w, http.StatusOK, map[string]string{"status": "ok", "model": s.cfg.MistralModel})
}

func (s *server) stats(w http.ResponseWriter, _ *http.Request) {
	respondJSON(w, http.StatusOK, s.store.Stats())
}

func (s *server) documents(w http.ResponseWriter, _ *http.Request) {
	respondJSON(w, http.StatusOK, compactDocuments(s.store.All()))
}

func (s *server) search(w http.ResponseWriter, r *http.Request) {
	respondJSON(w, http.StatusOK, compactDocuments(s.store.Search(r.URL.Query().Get("q"))))
}

func (s *server) documentByID(w http.ResponseWriter, r *http.Request) {
	id, action := parseDocumentPath(r.URL.Path)
	if action != "" {
		http.NotFound(w, r)
		return
	}
	document, ok := s.store.Get(id)
	if !ok {
		http.NotFound(w, r)
		return
	}
	respondJSON(w, http.StatusOK, document)
}

func (s *server) analyzeByID(w http.ResponseWriter, r *http.Request) {
	id, action := parseDocumentPath(r.URL.Path)
	if action != "analyze" {
		return
	}
	document, ok := s.store.Get(id)
	if !ok {
		http.NotFound(w, r)
		return
	}
	s.runAnalysis(&document)
	_ = s.store.Update(document)
	respondJSON(w, http.StatusOK, document)
}

func (s *server) upload(w http.ResponseWriter, r *http.Request) {
	if err := r.ParseMultipartForm(32 << 20); err != nil {
		respondError(w, http.StatusBadRequest, "upload invalido")
		return
	}

	file, header, err := r.FormFile("file")
	if err != nil {
		respondError(w, http.StatusBadRequest, "campo file nao encontrado")
		return
	}
	defer file.Close()

	id := newID()
	storedName := id + "-" + sanitizeFileName(header.Filename)
	targetPath := filepath.Join(s.cfg.StorageDir, "uploads", storedName)
	target, err := os.Create(targetPath)
	if err != nil {
		respondError(w, http.StatusInternalServerError, "falha ao salvar arquivo")
		return
	}
	defer target.Close()

	if _, err := io.Copy(target, file); err != nil {
		respondError(w, http.StatusInternalServerError, "falha ao gravar arquivo")
		return
	}

	text, err := extract.TextFromPath(targetPath, header.Filename)
	if err != nil {
		text = "Nao foi possivel extrair texto automaticamente: " + err.Error()
	}

	document := domain.Document{
		ID:         id,
		FileName:   header.Filename,
		StoredName: storedName,
		MimeType:   header.Header.Get("Content-Type"),
		Size:       header.Size,
		Text:       text,
		Preview:    preview(text),
		CreatedAt:  time.Now().UTC(),
	}
	s.runAnalysis(&document)

	if err := s.store.Add(document); err != nil {
		respondError(w, http.StatusInternalServerError, "falha ao salvar metadados")
		return
	}
	respondJSON(w, http.StatusCreated, document)
}

func (s *server) runAnalysis(document *domain.Document) {
	ctx, cancel := context.WithTimeout(context.Background(), 40*time.Second)
	defer cancel()

	insight, err := s.ai.Analyze(ctx, document.FileName, document.Text)
	if err != nil {
		log.Printf("mistral analysis fallback for %s: %v", document.FileName, err)
	}
	document.Insight = insight
	document.AnalyzedAt = time.Now().UTC()
}

func parseDocumentPath(path string) (string, string) {
	parts := strings.Split(strings.TrimPrefix(path, "/api/documents/"), "/")
	if len(parts) == 0 {
		return "", ""
	}
	action := ""
	if len(parts) > 1 {
		action = parts[1]
	}
	return parts[0], action
}

func compactDocuments(documents []domain.Document) []domain.Document {
	result := make([]domain.Document, len(documents))
	for index, document := range documents {
		document.Text = ""
		result[index] = document
	}
	return result
}

func respondJSON(w http.ResponseWriter, status int, payload any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	if err := json.NewEncoder(w).Encode(payload); err != nil {
		log.Printf("json response failed: %v", err)
	}
}

func respondError(w http.ResponseWriter, status int, message string) {
	respondJSON(w, status, map[string]string{"error": message})
}

func noCacheFileServer(dir string) http.Handler {
	files := http.FileServer(http.Dir(dir))
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
		w.Header().Set("Pragma", "no-cache")
		w.Header().Set("Expires", "0")
		files.ServeHTTP(w, r)
	})
}

func withCORS(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Access-Control-Allow-Origin", "*")
		w.Header().Set("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
		w.Header().Set("Access-Control-Allow-Headers", "Content-Type")
		if r.Method == http.MethodOptions {
			w.WriteHeader(http.StatusNoContent)
			return
		}
		next.ServeHTTP(w, r)
	})
}

func newID() string {
	buffer := make([]byte, 12)
	_, _ = rand.Read(buffer)
	return hex.EncodeToString(buffer)
}

func sanitizeFileName(name string) string {
	name = filepath.Base(name)
	name = strings.Map(func(r rune) rune {
		if r == '/' || r == '\\' || r == ':' {
			return '-'
		}
		return r
	}, name)
	return name
}

func preview(text string) string {
	text = strings.TrimSpace(text)
	if len(text) > 360 {
		return text[:360] + "..."
	}
	return text
}
