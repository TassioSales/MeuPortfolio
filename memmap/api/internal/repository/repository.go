package repository

import (
	"database/sql"
	"fmt"
	"os"
	"path/filepath"
	"time"

	"github.com/tassiosales/memmap/internal/domain"
	_ "modernc.org/sqlite"
)

const schema = `
CREATE TABLE IF NOT EXISTS notes (
	id         INTEGER PRIMARY KEY AUTOINCREMENT,
	title      TEXT    NOT NULL,
	content    TEXT    NOT NULL,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS entities (
	id      INTEGER PRIMARY KEY AUTOINCREMENT,
	note_id INTEGER NOT NULL,
	text    TEXT    NOT NULL,
	label   TEXT    NOT NULL,
	FOREIGN KEY(note_id) REFERENCES notes(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS edges (
	id      INTEGER PRIMARY KEY AUTOINCREMENT,
	note_id INTEGER NOT NULL,
	source  TEXT    NOT NULL,
	target  TEXT    NOT NULL,
	context TEXT,
	FOREIGN KEY(note_id) REFERENCES notes(id) ON DELETE CASCADE
);

PRAGMA foreign_keys = ON;
`

// Repository provides data-access methods backed by SQLite.
type Repository struct {
	db *sql.DB
}

// New opens (or creates) the SQLite database at dbPath and applies the schema.
func New(dbPath string) (*Repository, error) {
	// Ensure parent directory exists
	dir := filepath.Dir(dbPath)
	if err := os.MkdirAll(dir, 0755); err != nil {
		return nil, fmt.Errorf("create db dir: %w", err)
	}

	db, err := sql.Open("sqlite", dbPath)
	if err != nil {
		return nil, fmt.Errorf("open sqlite: %w", err)
	}

	// Enable WAL mode for better concurrency
	if _, err := db.Exec("PRAGMA journal_mode=WAL;"); err != nil {
		return nil, fmt.Errorf("enable WAL: %w", err)
	}

	if _, err := db.Exec(schema); err != nil {
		return nil, fmt.Errorf("apply schema: %w", err)
	}

	return &Repository{db: db}, nil
}

// Close closes the underlying database connection.
func (r *Repository) Close() error {
	return r.db.Close()
}

// ---- Notes ----

// ListNotes returns all notes ordered by updated_at DESC.
func (r *Repository) ListNotes() ([]domain.Note, error) {
	rows, err := r.db.Query(
		`SELECT id, title, content, created_at, updated_at FROM notes ORDER BY updated_at DESC`,
	)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var notes []domain.Note
	for rows.Next() {
		var n domain.Note
		if err := rows.Scan(&n.ID, &n.Title, &n.Content, &n.CreatedAt, &n.UpdatedAt); err != nil {
			return nil, err
		}
		notes = append(notes, n)
	}
	return notes, rows.Err()
}

// GetNote returns a single note by ID.
func (r *Repository) GetNote(id int64) (*domain.Note, error) {
	var n domain.Note
	err := r.db.QueryRow(
		`SELECT id, title, content, created_at, updated_at FROM notes WHERE id = ?`, id,
	).Scan(&n.ID, &n.Title, &n.Content, &n.CreatedAt, &n.UpdatedAt)
	if err == sql.ErrNoRows {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}
	return &n, nil
}

// CreateNote inserts a note and its associated entities and edges in a transaction.
func (r *Repository) CreateNote(req domain.CreateNoteRequest) (*domain.Note, error) {
	tx, err := r.db.Begin()
	if err != nil {
		return nil, err
	}
	defer tx.Rollback() //nolint:errcheck

	now := time.Now().UTC()

	res, err := tx.Exec(
		`INSERT INTO notes (title, content, created_at, updated_at) VALUES (?, ?, ?, ?)`,
		req.Title, req.Content, now, now,
	)
	if err != nil {
		return nil, err
	}
	noteID, err := res.LastInsertId()
	if err != nil {
		return nil, err
	}

	for _, e := range req.Entities {
		if _, err := tx.Exec(
			`INSERT INTO entities (note_id, text, label) VALUES (?, ?, ?)`,
			noteID, e.Text, e.Label,
		); err != nil {
			return nil, err
		}
	}

	for _, rel := range req.Relations {
		if _, err := tx.Exec(
			`INSERT INTO edges (note_id, source, target, context) VALUES (?, ?, ?, ?)`,
			noteID, rel.Source, rel.Target, rel.Context,
		); err != nil {
			return nil, err
		}
	}

	if err := tx.Commit(); err != nil {
		return nil, err
	}

	return &domain.Note{
		ID:        noteID,
		Title:     req.Title,
		Content:   req.Content,
		CreatedAt: now,
		UpdatedAt: now,
	}, nil
}

// DeleteNote removes a note and all its entities/edges (cascade).
func (r *Repository) DeleteNote(id int64) error {
	_, err := r.db.Exec(`DELETE FROM notes WHERE id = ?`, id)
	return err
}

// ---- Graph ----

// GetGraphData builds the aggregated GraphData from all stored entities and edges.
func (r *Repository) GetGraphData() (*domain.GraphData, error) {
	// Aggregate nodes: unique entity text → label + count
	nodeRows, err := r.db.Query(
		`SELECT text, label, COUNT(*) as cnt FROM entities GROUP BY text, label ORDER BY cnt DESC`,
	)
	if err != nil {
		return nil, err
	}
	defer nodeRows.Close()

	nodeMap := make(map[string]*domain.GraphNode)
	var nodes []domain.GraphNode

	for nodeRows.Next() {
		var text, label string
		var cnt int
		if err := nodeRows.Scan(&text, &label, &cnt); err != nil {
			return nil, err
		}
		if existing, ok := nodeMap[text]; ok {
			existing.Count += cnt
		} else {
			node := domain.GraphNode{
				ID:    text,
				Label: text,
				Group: label,
				Count: cnt,
			}
			nodeMap[text] = &node
			nodes = append(nodes, node)
		}
	}
	if err := nodeRows.Err(); err != nil {
		return nil, err
	}

	// Aggregate links: deduplicate by (source, target)
	edgeRows, err := r.db.Query(
		`SELECT source, target, context FROM edges`,
	)
	if err != nil {
		return nil, err
	}
	defer edgeRows.Close()

	type linkKey struct{ src, tgt string }
	linkMap := make(map[linkKey]*domain.GraphLink)
	var links []domain.GraphLink

	for edgeRows.Next() {
		var src, tgt, ctx string
		if err := edgeRows.Scan(&src, &tgt, &ctx); err != nil {
			return nil, err
		}
		key := linkKey{src, tgt}
		if _, exists := linkMap[key]; !exists {
			link := domain.GraphLink{Source: src, Target: tgt, Context: ctx}
			linkMap[key] = &link
			links = append(links, link)
		}
	}
	if err := edgeRows.Err(); err != nil {
		return nil, err
	}

	if nodes == nil {
		nodes = []domain.GraphNode{}
	}
	if links == nil {
		links = []domain.GraphLink{}
	}

	return &domain.GraphData{Nodes: nodes, Links: links}, nil
}
