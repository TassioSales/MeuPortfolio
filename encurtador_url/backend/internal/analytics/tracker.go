package analytics

import (
	"net/http"

	"encurtador_url/backend/internal/storage"
)

// Tracker records click analytics.
type Tracker struct {
	db *storage.DB
}

// New creates a new Tracker.
func New(db *storage.DB) *Tracker {
	return &Tracker{db: db}
}

// Record saves a click event derived from the HTTP request.
func (t *Tracker) Record(urlID int64, r *http.Request) error {
	referer := r.Referer()
	userAgent := r.UserAgent()
	return t.db.RecordClick(urlID, referer, userAgent)
}
