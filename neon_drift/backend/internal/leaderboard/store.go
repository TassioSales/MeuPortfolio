package leaderboard

import (
	"sort"
	"sync"
	"time"
)

type Entry struct {
	Name      string    `json:"name"`
	Score     int       `json:"score"`
	Distance  float64   `json:"distance"`
	Duration  float64   `json:"duration"`
	CreatedAt time.Time `json:"createdAt"`
}

type Store struct {
	mu      sync.RWMutex
	limit   int
	entries []Entry
}

func NewStore(limit int) *Store {
	return &Store{limit: limit, entries: []Entry{}}
}

// Add stores a score under an exclusive lock, then keeps only the best entries.
// This lets simultaneous submissions stay deterministic without a database.
func (s *Store) Add(entry Entry) Entry {
	s.mu.Lock()
	defer s.mu.Unlock()

	s.entries = append(s.entries, entry)
	sortEntries(s.entries)
	if len(s.entries) > s.limit {
		s.entries = s.entries[:s.limit]
	}
	return entry
}

// Top returns a copy so callers cannot mutate shared leaderboard state.
func (s *Store) Top() []Entry {
	s.mu.RLock()
	defer s.mu.RUnlock()

	result := make([]Entry, len(s.entries))
	copy(result, s.entries)
	return result
}

func sortEntries(entries []Entry) {
	sort.SliceStable(entries, func(i, j int) bool {
		return entries[i].Score > entries[j].Score
	})
}
