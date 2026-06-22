package server

import (
	"encoding/json"
	"sync"

	"github.com/gorilla/websocket"
)

// Client is a single connected WebSocket client.
type Client struct {
	conn *websocket.Conn
	send chan []byte
}

// Hub manages all active WebSocket clients and broadcasts messages.
type Hub struct {
	clients   map[*Client]bool
	broadcast chan []byte
	register  chan *Client
	unregister chan *Client
	mu        sync.RWMutex
}

// NewHub creates and returns a new Hub. Call Run() in a goroutine.
func NewHub() *Hub {
	return &Hub{
		clients:    make(map[*Client]bool),
		broadcast:  make(chan []byte, 256),
		register:   make(chan *Client),
		unregister: make(chan *Client),
	}
}

// Run processes hub events. Must be called in its own goroutine.
func (h *Hub) Run() {
	for {
		select {
		case client := <-h.register:
			h.mu.Lock()
			h.clients[client] = true
			h.mu.Unlock()

		case client := <-h.unregister:
			h.mu.Lock()
			if _, ok := h.clients[client]; ok {
				delete(h.clients, client)
				close(client.send)
			}
			h.mu.Unlock()

		case message := <-h.broadcast:
			h.mu.RLock()
			for client := range h.clients {
				select {
				case client.send <- message:
				default:
					// Slow client — drop the message
				}
			}
			h.mu.RUnlock()
		}
	}
}

// Broadcast sends a JSON-marshalled payload to all connected clients.
func (h *Hub) Broadcast(v any) error {
	data, err := json.Marshal(v)
	if err != nil {
		return err
	}
	h.broadcast <- data
	return nil
}

// ServeWS upgrades an HTTP connection to WebSocket and registers the client.
func (h *Hub) ServeWS(conn *websocket.Conn) {
	client := &Client{conn: conn, send: make(chan []byte, 256)}
	h.register <- client

	// Write pump
	go func() {
		defer func() {
			h.unregister <- client
			conn.Close()
		}()
		for msg := range client.send {
			if err := conn.WriteMessage(websocket.TextMessage, msg); err != nil {
				return
			}
		}
	}()

	// Read pump (keep connection alive, handle pings/close)
	defer func() {
		h.unregister <- client
		conn.Close()
	}()
	for {
		if _, _, err := conn.ReadMessage(); err != nil {
			break
		}
	}
}
