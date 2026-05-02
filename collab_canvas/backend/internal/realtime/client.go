package realtime

import (
	"log"
	"strings"
	"time"

	"github.com/gorilla/websocket"
)

const (
	writeWait  = 10 * time.Second
	pongWait   = 60 * time.Second
	pingPeriod = (pongWait * 9) / 10
	sendBuffer = 256
	cooldown   = 3 * time.Second
)

type client struct {
	hub        *Hub
	conn       *websocket.Conn
	send       chan serverMessage
	lastDrawAt time.Time
}

func newClient(hub *Hub, conn *websocket.Conn) *client {
	return &client{
		hub:  hub,
		conn: conn,
		send: make(chan serverMessage, sendBuffer),
	}
}

func (c *client) readPump() {
	defer func() {
		c.hub.unregister <- c
		_ = c.conn.Close()
	}()

	c.conn.SetReadLimit(1024)
	_ = c.conn.SetReadDeadline(time.Now().Add(pongWait))
	c.conn.SetPongHandler(func(string) error {
		return c.conn.SetReadDeadline(time.Now().Add(pongWait))
	})

	for {
		var message clientMessage
		if err := c.conn.ReadJSON(&message); err != nil {
			if websocket.IsUnexpectedCloseError(err, websocket.CloseGoingAway, websocket.CloseAbnormalClosure) {
				log.Printf("websocket read error: %v", err)
			}
			return
		}

		c.handleMessage(message)
	}
}

func (c *client) handleMessage(message clientMessage) {
	switch message.Action {
	case "draw":
		c.handleDraw(message)
	default:
		c.sendError("unsupported action")
	}
}

func (c *client) handleDraw(message clientMessage) {
	color := strings.ToLower(strings.TrimSpace(message.Color))
	if !isHexColor(color) {
		c.sendError("invalid color")
		return
	}

	if remaining := c.remainingCooldown(); remaining > 0 {
		c.send <- serverMessage{
			Type:       "cooldown",
			RetryAfter: cooldownMillis(remaining),
		}
		return
	}

	if ok := c.hub.board.SetPixel(message.X, message.Y, color); !ok {
		c.sendError("pixel out of bounds")
		return
	}

	c.lastDrawAt = time.Now()
	c.hub.broadcast <- serverMessage{
		Type: "draw",
		Payload: drawPayload{
			X:     message.X,
			Y:     message.Y,
			Color: color,
		},
	}
}

func (c *client) remainingCooldown() time.Duration {
	if c.lastDrawAt.IsZero() {
		return 0
	}

	elapsed := time.Since(c.lastDrawAt)
	if elapsed >= cooldown {
		return 0
	}

	return cooldown - elapsed
}

func (c *client) sendError(message string) {
	c.send <- serverMessage{
		Type: "error",
		Payload: errorPayload{
			Message: message,
		},
	}
}

func isHexColor(color string) bool {
	if len(color) != 7 || color[0] != '#' {
		return false
	}

	for _, char := range color[1:] {
		if (char < '0' || char > '9') && (char < 'a' || char > 'f') {
			return false
		}
	}

	return true
}

func (c *client) writePump() {
	ticker := time.NewTicker(pingPeriod)
	defer func() {
		ticker.Stop()
		_ = c.conn.Close()
	}()

	for {
		select {
		case message, ok := <-c.send:
			_ = c.conn.SetWriteDeadline(time.Now().Add(writeWait))
			if !ok {
				_ = c.conn.WriteMessage(websocket.CloseMessage, []byte{})
				return
			}

			if err := c.conn.WriteJSON(message); err != nil {
				return
			}
		case <-ticker.C:
			_ = c.conn.SetWriteDeadline(time.Now().Add(writeWait))
			if err := c.conn.WriteMessage(websocket.PingMessage, nil); err != nil {
				return
			}
		}
	}
}
