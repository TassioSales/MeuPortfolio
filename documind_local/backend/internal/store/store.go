package store

import (
	"encoding/json"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"sync"

	"documind/backend/internal/domain"
)

type Store struct {
	mu        sync.RWMutex
	path      string
	documents []domain.Document
}

func New(path string) (*Store, error) {
	store := &Store{path: path}
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		return nil, err
	}
	_ = store.load()
	return store, nil
}

func (s *Store) Add(document domain.Document) error {
	s.mu.Lock()
	defer s.mu.Unlock()

	s.documents = append(s.documents, document)
	return s.saveLocked()
}

func (s *Store) Update(document domain.Document) error {
	s.mu.Lock()
	defer s.mu.Unlock()

	for index := range s.documents {
		if s.documents[index].ID == document.ID {
			s.documents[index] = document
			return s.saveLocked()
		}
	}
	return nil
}

func (s *Store) Delete(id string) (domain.Document, bool, error) {
	s.mu.Lock()
	defer s.mu.Unlock()

	for index, document := range s.documents {
		if document.ID == id {
			s.documents = append(s.documents[:index], s.documents[index+1:]...)
			return document, true, s.saveLocked()
		}
	}
	return domain.Document{}, false, nil
}

func (s *Store) All() []domain.Document {
	s.mu.RLock()
	defer s.mu.RUnlock()

	result := make([]domain.Document, len(s.documents))
	copy(result, s.documents)
	sort.SliceStable(result, func(i, j int) bool {
		return result[i].CreatedAt.After(result[j].CreatedAt)
	})
	return result
}

func (s *Store) Get(id string) (domain.Document, bool) {
	s.mu.RLock()
	defer s.mu.RUnlock()

	for _, document := range s.documents {
		if document.ID == id {
			return document, true
		}
	}
	return domain.Document{}, false
}

func (s *Store) HasStoredName(storedName string) bool {
	s.mu.RLock()
	defer s.mu.RUnlock()

	for _, document := range s.documents {
		if document.StoredName == storedName {
			return true
		}
	}
	return false
}

func (s *Store) Search(query string) []domain.Document {
	query = strings.ToLower(strings.TrimSpace(query))
	if query == "" {
		return s.All()
	}

	matches := []domain.Document{}
	for _, document := range s.All() {
		haystack := strings.ToLower(document.FileName + " " + document.Text + " " + strings.Join(document.Insight.Tags, " ") + " " + strings.Join(document.Insight.Entities, " "))
		if strings.Contains(haystack, query) {
			matches = append(matches, document)
		}
	}
	return matches
}

func (s *Store) Stats() domain.Stats {
	stats := domain.Stats{
		Tags:  map[string]int{},
		Risks: map[string]int{},
	}
	for _, document := range s.All() {
		stats.TotalDocuments++
		stats.TotalBytes += document.Size
		stats.TotalFlashcards += len(document.Study.Flashcards)
		stats.DueReviews += document.Study.Progress.DueCards
		stats.ReviewedCards += document.Study.Progress.ReviewedCards
		stats.Risks[document.Insight.RiskLevel]++
		for _, tag := range document.Insight.Tags {
			stats.Tags[tag]++
		}
	}
	return stats
}

func (s *Store) load() error {
	content, err := os.ReadFile(s.path)
	if err != nil {
		return err
	}
	return json.Unmarshal(content, &s.documents)
}

func (s *Store) saveLocked() error {
	content, err := json.MarshalIndent(s.documents, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(s.path, content, 0o644)
}
