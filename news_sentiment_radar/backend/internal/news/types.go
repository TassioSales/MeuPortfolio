package news

import "time"

type Source struct {
	Name   string `json:"name"`
	URL    string `json:"url"`
	Sector string `json:"sector"`
}

type Article struct {
	ID          string    `json:"id"`
	Title       string    `json:"title"`
	Description string    `json:"description"`
	Link        string    `json:"link"`
	Source      string    `json:"source"`
	PublishedAt time.Time `json:"publishedAt"`
	Sentiment   string    `json:"sentiment"`
	Score       int       `json:"score"`
	Sector      string    `json:"sector"`
	Entities    []string  `json:"entities"`
}

type Summary struct {
	UpdatedAt       time.Time       `json:"updatedAt"`
	TotalArticles   int             `json:"totalArticles"`
	AverageScore    float64         `json:"averageScore"`
	SentimentCounts map[string]int  `json:"sentimentCounts"`
	Sectors         []SectorSummary `json:"sectors"`
	TopEntities     []EntitySummary `json:"topEntities"`
}

type SectorSummary struct {
	Sector       string  `json:"sector"`
	Count        int     `json:"count"`
	AverageScore float64 `json:"averageScore"`
	Positive     int     `json:"positive"`
	Neutral      int     `json:"neutral"`
	Negative     int     `json:"negative"`
}

type EntitySummary struct {
	Name  string `json:"name"`
	Count int    `json:"count"`
}
