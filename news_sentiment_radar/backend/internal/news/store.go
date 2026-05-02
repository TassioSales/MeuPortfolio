package news

import (
	"context"
	"sort"
	"sync"
	"time"
)

type Store struct {
	mu        sync.RWMutex
	sources   []Source
	articles  []Article
	updatedAt time.Time
}

func NewStore(sources []Source) *Store {
	return &Store{
		sources:   sources,
		articles:  demoArticles(),
		updatedAt: time.Now().UTC(),
	}
}

// Refresh fetches sources outside the write lock, then swaps the article slice
// in one short critical section so API readers are not blocked by network IO.
func (s *Store) Refresh(ctx context.Context) int {
	collected := []Article{}
	for _, source := range s.sources {
		articles, err := FetchArticles(ctx, source)
		if err != nil {
			continue
		}
		collected = append(collected, articles...)
	}

	if len(collected) == 0 {
		return 0
	}

	sort.SliceStable(collected, func(i, j int) bool {
		return collected[i].PublishedAt.After(collected[j].PublishedAt)
	})

	seen := map[string]bool{}
	deduped := []Article{}
	for _, article := range collected {
		key := article.Link
		if key == "" {
			key = article.Title
		}
		if seen[key] || article.Title == "" {
			continue
		}
		seen[key] = true
		deduped = append(deduped, article)
		if len(deduped) == 150 {
			break
		}
	}

	s.mu.Lock()
	s.articles = deduped
	s.updatedAt = time.Now().UTC()
	s.mu.Unlock()
	return len(deduped)
}

func (s *Store) Sources() []Source {
	result := make([]Source, len(s.sources))
	copy(result, s.sources)
	return result
}

func (s *Store) Articles() []Article {
	s.mu.RLock()
	defer s.mu.RUnlock()

	result := make([]Article, len(s.articles))
	copy(result, s.articles)
	return result
}

func (s *Store) Summary() Summary {
	articles := s.Articles()
	s.mu.RLock()
	updatedAt := s.updatedAt
	s.mu.RUnlock()

	summary := Summary{
		UpdatedAt:       updatedAt,
		TotalArticles:   len(articles),
		SentimentCounts: map[string]int{"positivo": 0, "neutro": 0, "negativo": 0},
		Sectors:         []SectorSummary{},
		TopEntities:     []EntitySummary{},
	}

	if len(articles) == 0 {
		return summary
	}

	sectorMap := map[string]*SectorSummary{}
	entityMap := map[string]int{}
	totalScore := 0
	for _, article := range articles {
		totalScore += article.Score
		summary.SentimentCounts[article.Sentiment]++

		sector := sectorMap[article.Sector]
		if sector == nil {
			sector = &SectorSummary{Sector: article.Sector}
			sectorMap[article.Sector] = sector
		}
		sector.Count++
		sector.AverageScore += float64(article.Score)
		switch article.Sentiment {
		case "positivo":
			sector.Positive++
		case "negativo":
			sector.Negative++
		default:
			sector.Neutral++
		}

		for _, entity := range article.Entities {
			entityMap[entity]++
		}
	}

	summary.AverageScore = float64(totalScore) / float64(len(articles))
	for _, sector := range sectorMap {
		sector.AverageScore = sector.AverageScore / float64(sector.Count)
		summary.Sectors = append(summary.Sectors, *sector)
	}
	sort.SliceStable(summary.Sectors, func(i, j int) bool {
		return summary.Sectors[i].Count > summary.Sectors[j].Count
	})

	for entity, count := range entityMap {
		summary.TopEntities = append(summary.TopEntities, EntitySummary{Name: entity, Count: count})
	}
	sort.SliceStable(summary.TopEntities, func(i, j int) bool {
		return summary.TopEntities[i].Count > summary.TopEntities[j].Count
	})
	if len(summary.TopEntities) > 12 {
		summary.TopEntities = summary.TopEntities[:12]
	}

	return summary
}

func demoArticles() []Article {
	now := time.Now().UTC()
	return []Article{
		{
			ID: "demo-1", Title: "Mercado reage a queda da inflacao e bolsa avanca",
			Description: "Analistas veem melhora nas expectativas para juros.",
			Source:      "Demo", PublishedAt: now.Add(-1 * time.Hour), Sentiment: "positivo", Score: 2,
			Sector: "economia", Entities: []string{"Mercado", "Bolsa"},
		},
		{
			ID: "demo-2", Title: "Governo enfrenta crise apos denuncia no Congresso",
			Description: "Partidos cobram investigacao e novas votacoes podem atrasar.",
			Source:      "Demo", PublishedAt: now.Add(-2 * time.Hour), Sentiment: "negativo", Score: -3,
			Sector: "politica", Entities: []string{"Governo", "Congresso"},
		},
		{
			ID: "demo-3", Title: "Startup anuncia investimento em inteligencia artificial",
			Description: "Empresa pretende expandir equipe de dados e software.",
			Source:      "Demo", PublishedAt: now.Add(-3 * time.Hour), Sentiment: "positivo", Score: 2,
			Sector: "tecnologia", Entities: []string{"Startup", "Inteligencia Artificial"},
		},
		{
			ID: "demo-4", Title: "Saude em alerta por novo surto de dengue",
			Description: "Hospitais reforcam atendimento e municipios ampliam prevencao.",
			Source:      "Demo", PublishedAt: now.Add(-4 * time.Hour), Sentiment: "negativo", Score: -2,
			Sector: "saude", Entities: []string{"Saude", "Dengue"},
		},
	}
}
