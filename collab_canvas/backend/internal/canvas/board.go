package canvas

import "sync"

// Board keeps the pixel matrix in memory and protects it with an RWMutex.
// Writers take the exclusive lock, while snapshots can be served concurrently.
type Board struct {
	mu     sync.RWMutex
	width  int
	height int
	pixels [][]string
}

func NewBoard(width, height int, fillColor string) *Board {
	pixels := make([][]string, height)
	for y := range pixels {
		pixels[y] = make([]string, width)
		for x := range pixels[y] {
			pixels[y][x] = fillColor
		}
	}

	return &Board{
		width:  width,
		height: height,
		pixels: pixels,
	}
}

func (b *Board) Width() int {
	return b.width
}

func (b *Board) Height() int {
	return b.height
}

// SetPixel validates the grid position and updates one cell while holding the
// exclusive lock, preventing overlapping draws from racing on the same matrix.
func (b *Board) SetPixel(x, y int, color string) bool {
	b.mu.Lock()
	defer b.mu.Unlock()

	if x < 0 || y < 0 || x >= b.width || y >= b.height {
		return false
	}

	b.pixels[y][x] = color
	return true
}

// Snapshot returns a deep copy so WebSocket clients can serialize the board
// without holding the read lock during network writes.
func (b *Board) Snapshot() [][]string {
	b.mu.RLock()
	defer b.mu.RUnlock()

	copyPixels := make([][]string, b.height)
	for y := range b.pixels {
		copyPixels[y] = make([]string, b.width)
		copy(copyPixels[y], b.pixels[y])
	}

	return copyPixels
}
