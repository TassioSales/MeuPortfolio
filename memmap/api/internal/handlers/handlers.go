package handlers

import (
	"encoding/json"
	"log"
	"net/http"
	"strconv"

	"github.com/go-chi/chi/v5"
	"github.com/gorilla/websocket"
	"github.com/tassiosales/memmap/internal/domain"
	"github.com/tassiosales/memmap/internal/repository"
	"github.com/tassiosales/memmap/internal/server"
)

var upgrader = websocket.Upgrader{
	ReadBufferSize:  1024,
	WriteBufferSize: 1024,
	CheckOrigin: func(r *http.Request) bool {
		// Allow all origins in development; restrict in production via config.
		return true
	},
}

// Handler holds dependencies for HTTP handlers.
type Handler struct {
	repo *repository.Repository
	hub  *server.Hub
}

// New creates a Handler with the given repository and WebSocket hub.
func New(repo *repository.Repository, hub *server.Hub) *Handler {
	return &Handler{repo: repo, hub: hub}
}

// respond writes a JSON response.
func respond(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	if err := json.NewEncoder(w).Encode(v); err != nil {
		log.Printf("encode response: %v", err)
	}
}

// respondError writes a JSON error response.
func respondError(w http.ResponseWriter, status int, msg string) {
	respond(w, status, map[string]string{"error": msg})
}

// broadcastGraph fetches the current graph and pushes it to all WebSocket clients.
func (h *Handler) broadcastGraph() {
	graph, err := h.repo.GetGraphData()
	if err != nil {
		log.Printf("broadcastGraph: get graph: %v", err)
		return
	}
	if err := h.hub.Broadcast(graph); err != nil {
		log.Printf("broadcastGraph: broadcast: %v", err)
	}
}

// ListNotes handles GET /notes
func (h *Handler) ListNotes(w http.ResponseWriter, r *http.Request) {
	notes, err := h.repo.ListNotes()
	if err != nil {
		respondError(w, http.StatusInternalServerError, "failed to list notes")
		return
	}
	if notes == nil {
		notes = []domain.Note{}
	}
	respond(w, http.StatusOK, notes)
}

// CreateNote handles POST /notes
func (h *Handler) CreateNote(w http.ResponseWriter, r *http.Request) {
	var req domain.CreateNoteRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		respondError(w, http.StatusBadRequest, "invalid request body")
		return
	}
	if req.Title == "" {
		respondError(w, http.StatusBadRequest, "title is required")
		return
	}

	note, err := h.repo.CreateNote(req)
	if err != nil {
		log.Printf("CreateNote: %v", err)
		respondError(w, http.StatusInternalServerError, "failed to create note")
		return
	}

	go h.broadcastGraph()

	respond(w, http.StatusCreated, note)
}

// GetNote handles GET /notes/{id}
func (h *Handler) GetNote(w http.ResponseWriter, r *http.Request) {
	id, err := strconv.ParseInt(chi.URLParam(r, "id"), 10, 64)
	if err != nil {
		respondError(w, http.StatusBadRequest, "invalid note id")
		return
	}

	note, err := h.repo.GetNote(id)
	if err != nil {
		respondError(w, http.StatusInternalServerError, "failed to get note")
		return
	}
	if note == nil {
		respondError(w, http.StatusNotFound, "note not found")
		return
	}

	respond(w, http.StatusOK, note)
}

// DeleteNote handles DELETE /notes/{id}
func (h *Handler) DeleteNote(w http.ResponseWriter, r *http.Request) {
	id, err := strconv.ParseInt(chi.URLParam(r, "id"), 10, 64)
	if err != nil {
		respondError(w, http.StatusBadRequest, "invalid note id")
		return
	}

	if err := h.repo.DeleteNote(id); err != nil {
		respondError(w, http.StatusInternalServerError, "failed to delete note")
		return
	}

	go h.broadcastGraph()

	w.WriteHeader(http.StatusNoContent)
}

// GetGraph handles GET /graph
func (h *Handler) GetGraph(w http.ResponseWriter, r *http.Request) {
	graph, err := h.repo.GetGraphData()
	if err != nil {
		respondError(w, http.StatusInternalServerError, "failed to build graph")
		return
	}
	respond(w, http.StatusOK, graph)
}

// HandleWS handles GET /ws — upgrades to WebSocket
func (h *Handler) HandleWS(w http.ResponseWriter, r *http.Request) {
	conn, err := upgrader.Upgrade(w, r, nil)
	if err != nil {
		log.Printf("ws upgrade: %v", err)
		return
	}

	// Send the current graph immediately on connect
	graph, err := h.repo.GetGraphData()
	if err == nil {
		data, _ := json.Marshal(graph)
		_ = conn.WriteMessage(websocket.TextMessage, data)
	}

	h.hub.ServeWS(conn)
}
