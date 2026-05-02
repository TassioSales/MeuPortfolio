package domain

import "time"

type Document struct {
	ID         string    `json:"id"`
	FileName   string    `json:"fileName"`
	StoredName string    `json:"storedName"`
	MimeType   string    `json:"mimeType"`
	Size       int64     `json:"size"`
	Text       string    `json:"text"`
	Preview    string    `json:"preview"`
	Insight    Insight   `json:"insight"`
	CreatedAt  time.Time `json:"createdAt"`
	AnalyzedAt time.Time `json:"analyzedAt,omitempty"`
}

type Insight struct {
	Summary          string   `json:"summary"`
	DocumentType     string   `json:"documentType"`
	Tags             []string `json:"tags"`
	Entities         []string `json:"entities"`
	SuggestedActions []string `json:"suggestedActions"`
	RiskLevel        string   `json:"riskLevel"`
}

type Stats struct {
	TotalDocuments int            `json:"totalDocuments"`
	TotalBytes     int64          `json:"totalBytes"`
	Tags           map[string]int `json:"tags"`
	Risks          map[string]int `json:"risks"`
}
