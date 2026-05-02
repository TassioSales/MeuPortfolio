package scores

import (
	"sort"
	"sync"
	"time"
)

type Entry struct {
	Name      string    `json:"name"`
	Score     int       `json:"score"`
	Length    int       `json:"length"`
	CreatedAt time.Time `json:"createdAt"`
}

type Store struct {
	mu      sync.RWMutex
	limit   int
	entries []Entry
}

func NewStore(limit int) *Store {
	return &Store{limit: limit}
}

// Add is protected by a mutex because score submissions can arrive together.
func (s *Store) Add(entry Entry) Entry {
	s.mu.Lock()
	defer s.mu.Unlock()

	s.entries = append(s.entries, entry)
	sort.SliceStable(s.entries, func(i, j int) bool {
		return s.entries[i].Score > s.entries[j].Score
	})
	if len(s.entries) > s.limit {
		s.entries = s.entries[:s.limit]
	}
	return entry
}

func (s *Store) Top() []Entry {
	s.mu.RLock()
	defer s.mu.RUnlock()

	result := make([]Entry, len(s.entries))
	copy(result, s.entries)
	return result
}
