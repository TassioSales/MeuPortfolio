package storage

import (
	"database/sql"
	"fmt"
	"os"
	"time"

	_ "modernc.org/sqlite"
)

type URL struct {
	ID          int64     `json:"id"`
	ShortCode   string    `json:"short_code"`
	OriginalURL string    `json:"original_url"`
	CreatedAt   time.Time `json:"created_at"`
	ClickCount  int       `json:"click_count"`
}

type Click struct {
	ID        int64     `json:"id"`
	URLID     int64     `json:"url_id"`
	ClickedAt time.Time `json:"clicked_at"`
	Referer   string    `json:"referer"`
	UserAgent string    `json:"user_agent"`
}

type DailyStat struct {
	Date  string `json:"date"`
	Count int    `json:"count"`
}

type DB struct {
	conn *sql.DB
}

func Open() (*DB, error) {
	path := os.Getenv("DB_PATH")
	if path == "" {
		path = "./encurtador.db"
	}

	conn, err := sql.Open("sqlite", path)
	if err != nil {
		return nil, fmt.Errorf("open db: %w", err)
	}

	db := &DB{conn: conn}
	if err := db.migrate(); err != nil {
		return nil, fmt.Errorf("migrate: %w", err)
	}

	return db, nil
}

func (db *DB) migrate() error {
	_, err := db.conn.Exec(`
		CREATE TABLE IF NOT EXISTS urls (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			short_code TEXT UNIQUE NOT NULL,
			original_url TEXT NOT NULL,
			created_at DATETIME DEFAULT CURRENT_TIMESTAMP
		);
		CREATE TABLE IF NOT EXISTS clicks (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			url_id INTEGER REFERENCES urls(id),
			clicked_at DATETIME DEFAULT CURRENT_TIMESTAMP,
			referer TEXT,
			user_agent TEXT
		);
	`)
	return err
}

func (db *DB) Close() error {
	return db.conn.Close()
}

// InsertURL inserts a new short URL and returns the inserted row.
func (db *DB) InsertURL(shortCode, originalURL string) (*URL, error) {
	res, err := db.conn.Exec(
		`INSERT INTO urls (short_code, original_url) VALUES (?, ?)`,
		shortCode, originalURL,
	)
	if err != nil {
		return nil, err
	}
	id, _ := res.LastInsertId()
	return db.GetURLByCode(shortCode, id)
}

// GetURLByCode fetches a URL row by short code. id is optional (pass 0 to ignore).
func (db *DB) GetURLByCode(shortCode string, id int64) (*URL, error) {
	query := `SELECT id, short_code, original_url, created_at FROM urls WHERE short_code = ?`
	row := db.conn.QueryRow(query, shortCode)
	u := &URL{}
	var createdAt string
	if err := row.Scan(&u.ID, &u.ShortCode, &u.OriginalURL, &createdAt); err != nil {
		return nil, err
	}
	u.CreatedAt, _ = time.Parse("2006-01-02 15:04:05", createdAt)
	return u, nil
}

// CodeExists returns true if the short code already exists in the DB.
func (db *DB) CodeExists(shortCode string) (bool, error) {
	var count int
	err := db.conn.QueryRow(`SELECT COUNT(*) FROM urls WHERE short_code = ?`, shortCode).Scan(&count)
	return count > 0, err
}

// GetByOriginalURL returns an existing URL row for the given original URL, or nil if not found.
func (db *DB) GetByOriginalURL(originalURL string) (*URL, error) {
	query := `SELECT id, short_code, original_url, created_at FROM urls WHERE original_url = ? LIMIT 1`
	row := db.conn.QueryRow(query, originalURL)
	u := &URL{}
	var createdAt string
	if err := row.Scan(&u.ID, &u.ShortCode, &u.OriginalURL, &createdAt); err != nil {
		if err == sql.ErrNoRows {
			return nil, nil
		}
		return nil, err
	}
	u.CreatedAt, _ = time.Parse("2006-01-02 15:04:05", createdAt)
	return u, nil
}

// ListURLs returns all URLs with their click counts.
func (db *DB) ListURLs() ([]URL, error) {
	rows, err := db.conn.Query(`
		SELECT u.id, u.short_code, u.original_url, u.created_at,
		       COUNT(c.id) AS click_count
		FROM urls u
		LEFT JOIN clicks c ON c.url_id = u.id
		GROUP BY u.id
		ORDER BY u.created_at DESC
	`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var urls []URL
	for rows.Next() {
		var u URL
		var createdAt string
		if err := rows.Scan(&u.ID, &u.ShortCode, &u.OriginalURL, &createdAt, &u.ClickCount); err != nil {
			return nil, err
		}
		u.CreatedAt, _ = time.Parse("2006-01-02 15:04:05", createdAt)
		urls = append(urls, u)
	}
	return urls, rows.Err()
}

// RecordClick inserts a click event for the given URL id.
func (db *DB) RecordClick(urlID int64, referer, userAgent string) error {
	_, err := db.conn.Exec(
		`INSERT INTO clicks (url_id, referer, user_agent) VALUES (?, ?, ?)`,
		urlID, referer, userAgent,
	)
	return err
}

// GetDailyStats returns clicks per day for the last 30 days for a short code.
func (db *DB) GetDailyStats(shortCode string) ([]DailyStat, error) {
	rows, err := db.conn.Query(`
		SELECT DATE(c.clicked_at) AS day, COUNT(*) AS count
		FROM clicks c
		JOIN urls u ON u.id = c.url_id
		WHERE u.short_code = ?
		  AND c.clicked_at >= DATE('now', '-30 days')
		GROUP BY day
		ORDER BY day ASC
	`, shortCode)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var stats []DailyStat
	for rows.Next() {
		var s DailyStat
		if err := rows.Scan(&s.Date, &s.Count); err != nil {
			return nil, err
		}
		stats = append(stats, s)
	}
	return stats, rows.Err()
}
