package news

import "testing"

func TestSummaryAggregatesArticles(t *testing.T) {
	store := NewStore(nil)
	summary := store.Summary()

	if summary.TotalArticles == 0 {
		t.Fatal("expected demo articles")
	}
	if len(summary.Sectors) == 0 {
		t.Fatal("expected sector summaries")
	}
	if len(summary.TopEntities) == 0 {
		t.Fatal("expected top entities")
	}
}
