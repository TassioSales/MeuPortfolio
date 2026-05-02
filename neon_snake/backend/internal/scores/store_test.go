package scores

import "testing"

func TestStoreSortsScores(t *testing.T) {
	store := NewStore(2)

	store.Add(Entry{Name: "Low", Score: 5})
	store.Add(Entry{Name: "High", Score: 50})
	store.Add(Entry{Name: "Mid", Score: 25})

	top := store.Top()
	if len(top) != 2 || top[0].Name != "High" || top[1].Name != "Mid" {
		t.Fatalf("unexpected top scores: %#v", top)
	}
}
