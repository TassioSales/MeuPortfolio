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
	return s.GenerateInsightsWithKey(username, m, "")
}

func (s *InsightsService) GenerateInsightsWithKey(username string, m *metrics.Metrics, keyOverride string) ([]string, error) {
	key := keyOverride
	if key == "" {
		key = s.apiKey
	}
	if key == "" {
		return []string{"Configure sua chave da Mistral AI para gerar insights sobre este perfil."}, nil
	}

	prompt := fmt.Sprintf(`Analise este perfil de desenvolvedor no GitHub e forneça de 4 a 5 insights concisos e acionáveis em português do Brasil.
Foque em pontos fortes, padrões observados e sugestões de melhoria.

Desenvolvedor: %s
Repositórios públicos: %d
Total de estrelas: %d
Total de forks: %d
Linguagem mais usada: %s
Top linguagens: `, username, m.TotalRepos, m.TotalStars, m.TotalForks, m.MostUsedLang)

	for i, lang := range m.Languages {
		if i > 0 {
			prompt += ", "
		}
		if i >= 5 {
			break
		}
		prompt += fmt.Sprintf("%s (%.1f%%)", lang.Language, lang.Percentage)
	}

	prompt += "\n\nRetorne APENAS um array JSON de strings, cada string sendo um insight. Responda somente em português do Brasil. Exemplo: [\"insight 1\", \"insight 2\"]"

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
	req.Header.Set("Authorization", "Bearer "+key)

	resp, err := s.httpClient.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("mistral API retornou status %d", resp.StatusCode)
	}

	var mistralResp mistralResponse
	if err := json.NewDecoder(resp.Body).Decode(&mistralResp); err != nil {
		return nil, err
	}

	if len(mistralResp.Choices) == 0 {
		return nil, fmt.Errorf("nenhuma resposta retornada pela Mistral")
	}

	content := mistralResp.Choices[0].Message.Content
	var insights []string
	if err := json.Unmarshal([]byte(content), &insights); err != nil {
		return []string{content}, nil
	}
	return insights, nil
}
