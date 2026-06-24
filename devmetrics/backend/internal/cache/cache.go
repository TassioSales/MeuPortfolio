package cache

import (
	"sync"
	"time"
)

type entry struct {
	value     interface{}
	expiresAt time.Time
}

type Cache struct {
	mu  sync.RWMutex
	ttl time.Duration
	m   map[string]entry
}

func New(ttl time.Duration) *Cache {
	c := &Cache{ttl: ttl, m: make(map[string]entry)}
	go c.evict()
	return c
}

func (c *Cache) Get(key string) (interface{}, bool) {
	c.mu.RLock()
	defer c.mu.RUnlock()
	e, ok := c.m[key]
	if !ok || time.Now().After(e.expiresAt) {
		return nil, false
	}
	return e.value, true
}

func (c *Cache) Set(key string, value interface{}) {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.m[key] = entry{value: value, expiresAt: time.Now().Add(c.ttl)}
}

func (c *Cache) evict() {
	ticker := time.NewTicker(c.ttl)
	for range ticker.C {
		c.mu.Lock()
		now := time.Now()
		for k, e := range c.m {
			if now.After(e.expiresAt) {
				delete(c.m, k)
			}
		}
		c.mu.Unlock()
	}
}
