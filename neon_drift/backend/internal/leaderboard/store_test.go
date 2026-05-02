package leaderboard

import "testing"

func TestStoreKeepsBestScores(t *testing.T) {
	store := NewStore(2)

	store.Add(Entry{Name: "A", Score: 10})
	store.Add(Entry{Name: "B", Score: 30})
	store.Add(Entry{Name: "C", Score: 20})

	top := store.Top()
	if len(top) != 2 {
		t.Fatalf("expected 2 entries, got %d", len(top))
	}
	if top[0].Name != "B" || top[1].Name != "C" {
		t.Fatalf("unexpected ranking: %#v", top)
	}
}
