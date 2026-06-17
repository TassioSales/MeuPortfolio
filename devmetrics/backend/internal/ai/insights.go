package ai

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"time"

	"devmetrics/backend/internal/metrics"
)

type InsightsService struct {
	apiKey     string
	httpClient *http.Client
}

type mistralMessage struct {
	Role    string `json:"role"`
	Content string `json:"content"`
}

type mistralRequest struct {
	Model    string           `json:"model"`
	Messages []mistralMessage `json:"messages"`
}

type mistralChoice struct {
	Message mistralMessage `json:"message"`
}

type mistralResponse struct {
	Choices []mistralChoice `json:"choices"`
}

func NewInsightsService(apiKey string) *InsightsService {
	return &InsightsService{
		apiKey:     apiKey,
		httpClient: &http.Client{Timeout: 30 * time.Second},
	}
}

func (s *InsightsService) GenerateInsights(username string, m *metrics.Metrics) ([]string, error) {
	if s.apiKey == "" {
		return []string{"Configure MISTRAL_API_KEY to enable AI insights."}, nil
	}

	prompt := fmt.Sprintf(`Analyze this GitHub developer profile and provide 4-5 concise, actionable insights in English.
Focus on strengths, patterns, and suggestions.

Developer: %s
Public Repos: %d
Total Stars: %d
Total Forks: %d
Most Used Language: %s
Top Languages: `, username, m.TotalRepos, m.TotalStars, m.TotalForks, m.MostUsedLang)

	for i, lang := range m.Languages {
		if i > 0 {
			prompt += ", "
		}
		if i >= 5 {
			break
		}
		prompt += fmt.Sprintf("%s (%.1f%%)", lang.Language, lang.Percentage)
	}

	prompt += "\n\nReturn ONLY a JSON array of strings, each string being one insight bullet point. Example: [\"insight 1\", \"insight 2\"]"

	reqBody := mistralRequest{
		Model: "mistral-small-latest",
		Messages: []mistralMessage{
			{Role: "user", Content: prompt},
		},
	}

	bodyBytes, err := json.Marshal(reqBody)
	if err != nil {
		return nil, err
	}

	req, err := http.NewRequest("POST", "https://api.mistral.ai/v1/chat/completions", bytes.NewReader(bodyBytes))
	if err != nil {
		return nil, err
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Authorization", "Bearer "+s.apiKey)

	resp, err := s.httpClient.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("mistral API returned status %d", resp.StatusCode)
	}

	var mistralResp mistralResponse
	if err := json.NewDecoder(resp.Body).Decode(&mistralResp); err != nil {
		return nil, err
	}

	if len(mistralResp.Choices) == 0 {
		return nil, fmt.Errorf("no choices returned from Mistral")
	}

	content := mistralResp.Choices[0].Message.Content
	var insights []string
	if err := json.Unmarshal([]byte(content), &insights); err != nil {
		// fallback: return raw content as single item
		return []string{content}, nil
	}
	return insights, nil
}
