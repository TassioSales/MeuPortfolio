package realtime

import "time"

type clientMessage struct {
	Action string `json:"action"`
	X      int    `json:"x"`
	Y      int    `json:"y"`
	Color  string `json:"color"`
}

type serverMessage struct {
	Type       string     `json:"type"`
	Width      int        `json:"width,omitempty"`
	Height     int        `json:"height,omitempty"`
	Pixels     [][]string `json:"pixels,omitempty"`
	Users      int        `json:"users,omitempty"`
	Payload    any        `json:"payload,omitempty"`
	RetryAfter int        `json:"retryAfterMs,omitempty"`
}

type drawPayload struct {
	X     int    `json:"x"`
	Y     int    `json:"y"`
	Color string `json:"color"`
}

type errorPayload struct {
	Message string `json:"message"`
}

func cooldownMillis(remaining time.Duration) int {
	if remaining <= 0 {
		return 0
	}

	return int(remaining.Milliseconds())
}
