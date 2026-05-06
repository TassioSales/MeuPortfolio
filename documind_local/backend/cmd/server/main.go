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
	"regexp"
	"strings"
	"time"

	"documind/backend/internal/ai"
	"documind/backend/internal/config"
	"documind/backend/internal/domain"
	"documind/backend/internal/extract"
	"documind/backend/internal/store"
	"documind/backend/internal/study"
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
	app.reconcileUploads()

	mux := http.NewServeMux()
	mux.HandleFunc("GET /api/health", app.health)
	mux.HandleFunc("GET /api/stats", app.stats)
	mux.HandleFunc("GET /api/documents", app.documents)
	mux.HandleFunc("POST /api/documents", app.upload)
	mux.HandleFunc("GET /api/search", app.search)
	mux.HandleFunc("GET /api/research", app.research)
	mux.HandleFunc("GET /api/documents/", app.documentByID)
	mux.HandleFunc("POST /api/documents/", app.analyzeByID)
	mux.HandleFunc("DELETE /api/documents/", app.deleteDocument)
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

func (s *server) research(w http.ResponseWriter, r *http.Request) {
	query := strings.TrimSpace(r.URL.Query().Get("q"))
	if query == "" {
		respondJSON(w, http.StatusOK, map[string]any{"query": "", "results": []any{}, "pdfQueries": []string{}})
		return
	}
	respondJSON(w, http.StatusOK, buildResearchSuggestions(query))
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
	if len(document.Study.Flashcards) == 0 {
		document.Study = study.BuildPlan(document.FileName, document.Text, document.Insight, time.Now())
		_ = s.store.Update(document)
	}
	respondJSON(w, http.StatusOK, document)
}

func (s *server) analyzeByID(w http.ResponseWriter, r *http.Request) {
	id, action := parseDocumentPath(r.URL.Path)
	if action == "review" {
		s.reviewFlashcard(w, r, id)
		return
	}
	if action != "analyze" {
		return
	}
	document, ok := s.store.Get(id)
	if !ok {
		http.NotFound(w, r)
		return
	}
	s.runAnalysis(&document)
	document.Study = study.BuildPlan(document.FileName, document.Text, document.Insight, time.Now())
	_ = s.store.Update(document)
	respondJSON(w, http.StatusOK, document)
}

func (s *server) deleteDocument(w http.ResponseWriter, r *http.Request) {
	id, action := parseDocumentPath(r.URL.Path)
	if action != "" {
		http.NotFound(w, r)
		return
	}
	document, ok, err := s.store.Delete(id)
	if err != nil {
		respondError(w, http.StatusInternalServerError, "falha ao apagar metadados")
		return
	}
	if !ok {
		http.NotFound(w, r)
		return
	}
	if document.StoredName != "" {
		_ = os.Remove(filepath.Join(s.cfg.StorageDir, "uploads", document.StoredName))
	}
	respondJSON(w, http.StatusOK, map[string]string{"status": "deleted"})
}

func (s *server) reviewFlashcard(w http.ResponseWriter, r *http.Request, id string) {
	var payload struct {
		CardID string `json:"cardId"`
		Result string `json:"result"`
	}
	if err := json.NewDecoder(r.Body).Decode(&payload); err != nil {
		respondError(w, http.StatusBadRequest, "revisao invalida")
		return
	}
	document, ok := s.store.Get(id)
	if !ok {
		http.NotFound(w, r)
		return
	}
	document.Study = study.Review(document.Study, payload.CardID, payload.Result, time.Now())
	if err := s.store.Update(document); err != nil {
		respondError(w, http.StatusInternalServerError, "falha ao salvar revisao")
		return
	}
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
	document.Study = study.BuildPlan(document.FileName, document.Text, document.Insight, time.Now())

	if err := s.store.Add(document); err != nil {
		respondError(w, http.StatusInternalServerError, "falha ao salvar metadados")
		return
	}
	respondJSON(w, http.StatusCreated, document)
}

func (s *server) reconcileUploads() {
	uploadDir := filepath.Join(s.cfg.StorageDir, "uploads")
	entries, err := os.ReadDir(uploadDir)
	if err != nil {
		return
	}
	for _, entry := range entries {
		if entry.IsDir() || entry.Name() == ".gitkeep" || s.store.HasStoredName(entry.Name()) {
			continue
		}
		path := filepath.Join(uploadDir, entry.Name())
		info, err := entry.Info()
		if err != nil {
			continue
		}
		fileName := originalNameFromStored(entry.Name())
		text, err := extract.TextFromPath(path, fileName)
		if err != nil {
			text = "Nao foi possivel extrair texto automaticamente: " + err.Error()
		}
		document := domain.Document{
			ID:         newID(),
			FileName:   fileName,
			StoredName: entry.Name(),
			Size:       info.Size(),
			Text:       text,
			Preview:    preview(text),
			CreatedAt:  info.ModTime().UTC(),
		}
		s.runAnalysis(&document)
		document.Study = study.BuildPlan(document.FileName, document.Text, document.Insight, time.Now())
		if err := s.store.Add(document); err != nil {
			log.Printf("upload reconciliation failed for %s: %v", entry.Name(), err)
		}
	}
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
		w.Header().Set("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
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

func originalNameFromStored(name string) string {
	pattern := regexp.MustCompile(`^[a-f0-9]{24}-(.+)$`)
	matches := pattern.FindStringSubmatch(name)
	if len(matches) == 2 {
		return matches[1]
	}
	return name
}

func buildResearchSuggestions(query string) map[string]any {
	encoded := strings.ReplaceAll(strings.TrimSpace(query), " ", "+")
	pdfQuery := query + " filetype:pdf"
	return map[string]any{
		"query": query,
		"pdfQueries": []string{
			pdfQuery,
			query + " apostila pdf",
			query + " exercicios resolvidos pdf",
			query + " resumo mapa mental pdf",
		},
		"results": []map[string]string{
			{
				"title": "Buscar PDFs no Google",
				"type":  "pdf",
				"url":   "https://www.google.com/search?q=" + encoded + "+filetype%3Apdf",
				"note":  "Use para encontrar apostilas, listas e materiais em PDF.",
			},
			{
				"title": "Buscar aulas e resumos",
				"type":  "tema",
				"url":   "https://www.google.com/search?q=" + encoded + "+resumo+exercicios",
				"note":  "Bom para montar objetivos e tópicos antes de subir arquivos.",
			},
			{
				"title": "Google Scholar",
				"type":  "academico",
				"url":   "https://scholar.google.com/scholar?q=" + encoded,
				"note":  "Útil para artigos, livros e materiais mais técnicos.",
			},
			{
				"title": "Internet Archive",
				"type":  "livros",
				"url":   "https://archive.org/search?query=" + encoded,
				"note":  "Pode ter livros e apostilas públicas para estudo.",
			},
		},
	}
}

func preview(text string) string {
	text = strings.TrimSpace(text)
	if len(text) > 360 {
		return text[:360] + "..."
	}
	return text
}
