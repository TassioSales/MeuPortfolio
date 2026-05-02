package realtime

import "testing"

func TestIsHexColor(t *testing.T) {
	tests := map[string]bool{
		"#000000": true,
		"#ff00aa": true,
		"#FF00AA": false,
		"ff00aa":  false,
		"#gg00aa": false,
		"#fff":    false,
	}

	for color, want := range tests {
		if got := isHexColor(color); got != want {
			t.Fatalf("isHexColor(%q) = %v, want %v", color, got, want)
		}
	}
}
