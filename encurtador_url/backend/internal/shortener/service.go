package shortener

import (
	"crypto/sha256"
	"fmt"
	"time"

	"encurtador_url/backend/internal/storage"
)

const base62Chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"

// Service handles URL shortening logic.
type Service struct {
	db *storage.DB
}

// New creates a new Service.
func New(db *storage.DB) *Service {
	return &Service{db: db}
}

// Shorten returns the existing short URL for originalURL if already stored,
// or creates a new one. This prevents duplicate entries for the same URL.
func (s *Service) Shorten(originalURL string) (*storage.URL, error) {
	// Deduplication: return existing short code if URL was already shortened.
	existing, err := s.db.GetByOriginalURL(originalURL)
	if err != nil {
		return nil, fmt.Errorf("check duplicate: %w", err)
	}
	if existing != nil {
		return existing, nil
	}

	for attempt := 0; attempt < 10; attempt++ {
		code := generateCode(originalURL, attempt)
		exists, err := s.db.CodeExists(code)
		if err != nil {
			return nil, fmt.Errorf("check collision: %w", err)
		}
		if exists {
			continue
		}
		url, err := s.db.InsertURL(code, originalURL)
		if err != nil {
			return nil, fmt.Errorf("insert url: %w", err)
		}
		return url, nil
	}
	return nil, fmt.Errorf("could not generate unique short code after 10 attempts")
}

// generateCode returns a 6-char base62 code from a SHA256 hash of url+timestamp+attempt.
func generateCode(url string, attempt int) string {
	seed := fmt.Sprintf("%s|%d|%d", url, time.Now().UnixNano(), attempt)
	hash := sha256.Sum256([]byte(seed))

	// Use first 8 bytes to get a big enough number.
	var num uint64
	for i := 0; i < 8; i++ {
		num = num<<8 | uint64(hash[i])
	}

	code := make([]byte, 6)
	for i := 5; i >= 0; i-- {
		code[i] = base62Chars[num%62]
		num /= 62
	}
	return string(code)
}
