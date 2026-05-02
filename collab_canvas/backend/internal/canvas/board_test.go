package canvas

import "testing"

func TestSetPixelUpdatesInBoundsPixel(t *testing.T) {
	board := NewBoard(2, 2, "#ffffff")

	if ok := board.SetPixel(1, 0, "#ff0000"); !ok {
		t.Fatal("expected in-bounds pixel to be updated")
	}

	snapshot := board.Snapshot()
	if snapshot[0][1] != "#ff0000" {
		t.Fatalf("expected updated pixel, got %q", snapshot[0][1])
	}
}

func TestSetPixelRejectsOutOfBoundsPixel(t *testing.T) {
	board := NewBoard(2, 2, "#ffffff")

	if ok := board.SetPixel(2, 0, "#ff0000"); ok {
		t.Fatal("expected out-of-bounds pixel to be rejected")
	}
}
