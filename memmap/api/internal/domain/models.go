package domain

import "time"

// Note represents a user note in the knowledge base.
type Note struct {
	ID        int64     `json:"id"`
	Title     string    `json:"title"`
	Content   string    `json:"content"`
	CreatedAt time.Time `json:"created_at"`
	UpdatedAt time.Time `json:"updated_at"`
}

// Entity represents a named entity extracted from a note.
type Entity struct {
	ID     int64  `json:"id"`
	NoteID int64  `json:"note_id"`
	Text   string `json:"text"`
	Label  string `json:"label"`
}

// Edge represents a directed relation between two entities.
type Edge struct {
	ID      int64  `json:"id"`
	Source  string `json:"source"`
	Target  string `json:"target"`
	Context string `json:"context"`
	NoteID  int64  `json:"note_id"`
}

// GraphData is the full graph payload sent to the frontend.
type GraphData struct {
	Nodes []GraphNode `json:"nodes"`
	Links []GraphLink `json:"links"`
}

// GraphNode is a node in the knowledge graph.
type GraphNode struct {
	ID    string `json:"id"`
	Label string `json:"label"`
	Group string `json:"group"` // entity type (PERSON, ORG, LOC, …)
	Count int    `json:"count"` // number of appearances
}

// GraphLink is an edge in the knowledge graph.
type GraphLink struct {
	Source  string `json:"source"`
	Target  string `json:"target"`
	Context string `json:"context"`
}

// CreateNoteRequest is the body expected by POST /notes.
type CreateNoteRequest struct {
	Title     string     `json:"title"`
	Content   string     `json:"content"`
	Entities  []Entity   `json:"entities"`
	Relations []Relation `json:"relations"`
}

// Relation is used in the create-note request to carry extracted relations.
type Relation struct {
	Source  string `json:"source"`
	Target  string `json:"target"`
	Context string `json:"context"`
}
