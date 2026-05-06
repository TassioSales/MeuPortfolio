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
	Study      StudyPlan `json:"study"`
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
	TotalDocuments  int            `json:"totalDocuments"`
	TotalBytes      int64          `json:"totalBytes"`
	TotalFlashcards int            `json:"totalFlashcards"`
	DueReviews      int            `json:"dueReviews"`
	ReviewedCards   int            `json:"reviewedCards"`
	Tags            map[string]int `json:"tags"`
	Risks           map[string]int `json:"risks"`
}

type StudyPlan struct {
	Title            string         `json:"title"`
	EstimatedMinutes int            `json:"estimatedMinutes"`
	Objectives       []string       `json:"objectives"`
	Topics           []StudyTopic   `json:"topics"`
	Schedule         []StudySession `json:"schedule"`
	Flashcards       []Flashcard    `json:"flashcards"`
	Progress         StudyProgress  `json:"progress"`
}

type StudyTopic struct {
	Name     string `json:"name"`
	Summary  string `json:"summary"`
	Priority string `json:"priority"`
}

type StudySession struct {
	ID              string    `json:"id"`
	Title           string    `json:"title"`
	DueDate         time.Time `json:"dueDate"`
	DurationMinutes int       `json:"durationMinutes"`
	Status          string    `json:"status"`
}

type Flashcard struct {
	ID           string     `json:"id"`
	Question     string     `json:"question"`
	Answer       string     `json:"answer"`
	DueDate      time.Time  `json:"dueDate"`
	IntervalDays int        `json:"intervalDays"`
	Ease         int        `json:"ease"`
	Reviews      int        `json:"reviews"`
	LastReviewed *time.Time `json:"lastReviewed,omitempty"`
	Status       string     `json:"status"`
}

type StudyProgress struct {
	TotalCards       int        `json:"totalCards"`
	DueCards         int        `json:"dueCards"`
	ReviewedCards    int        `json:"reviewedCards"`
	Completion       int        `json:"completion"`
	NextReview       *time.Time `json:"nextReview,omitempty"`
	EstimatedMinutes int        `json:"estimatedMinutes"`
}
