package realtime

import (
	"log"
	"net/http"

	"collabcanvas/backend/internal/canvas"

	"github.com/gorilla/websocket"
)

type Hub struct {
	board      *canvas.Board
	clients    map[*client]bool
	register   chan *client
	unregister chan *client
	broadcast  chan serverMessage
}

func NewHub(board *canvas.Board) *Hub {
	return &Hub{
		board:      board,
		clients:    make(map[*client]bool),
		register:   make(chan *client),
		unregister: make(chan *client),
		broadcast:  make(chan serverMessage, 256),
	}
}

// Run owns the clients map. All registration, unregistration and broadcasting
// happen through channels, which keeps WebSocket connection state race-free.
func (h *Hub) Run() {
	for {
		select {
		case client := <-h.register:
			h.clients[client] = true
			client.send <- h.initialStateMessage()
			h.sendToAll(h.presenceMessage())

		case client := <-h.unregister:
			if _, ok := h.clients[client]; ok {
				delete(h.clients, client)
				close(client.send)
				h.sendToAll(h.presenceMessage())
			}

		case message := <-h.broadcast:
			h.sendToAll(message)
		}
	}
}

func (h *Hub) ServeWS(w http.ResponseWriter, r *http.Request) {
	conn, err := upgrader.Upgrade(w, r, nil)
	if err != nil {
		log.Printf("websocket upgrade failed: %v", err)
		return
	}

	client := newClient(h, conn)
	h.register <- client

	go client.writePump()
	go client.readPump()
}

func (h *Hub) initialStateMessage() serverMessage {
	return serverMessage{
		Type:   "init",
		Width:  h.board.Width(),
		Height: h.board.Height(),
		Pixels: h.board.Snapshot(),
		Users:  len(h.clients),
	}
}

func (h *Hub) presenceMessage() serverMessage {
	return serverMessage{
		Type:  "presence",
		Users: len(h.clients),
	}
}

func (h *Hub) sendToAll(message serverMessage) {
	for client := range h.clients {
		select {
		case client.send <- message:
		default:
			close(client.send)
			delete(h.clients, client)
		}
	}
}

var upgrader = websocket.Upgrader{
	ReadBufferSize:  1024,
	WriteBufferSize: 1024,
	CheckOrigin: func(_ *http.Request) bool {
		return true
	},
}
