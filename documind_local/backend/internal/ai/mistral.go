package ai

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"net/http"
	"strings"
	"time"

	"documind/backend/internal/domain"
)

const endpoint = "https://api.mistral.ai/v1/chat/completions"

type Client struct {
	apiKey string
	model  string
	http   *http.Client
}

func NewClient(apiKey, model string) *Client {
	return &Client{
		apiKey: apiKey,
		model:  model,
		http:   &http.Client{Timeout: 35 * time.Second},
	}
}

func (c *Client) Analyze(ctx context.Context, fileName, text string) (domain.Insight, error) {
	if c.apiKey == "" {
		return fallbackInsight(text), errors.New("MISTRAL_API_KEY ausente")
	}

	prompt := buildPrompt(fileName, text)
	requestBody := chatRequest{
		Model:       c.model,
		Temperature: 0.2,
		MaxTokens:   700,
		Messages: []message{
			{Role: "system", Content: "Voce e um analista documental. Responda somente JSON valido, sem markdown."},
			{Role: "user", Content: prompt},
		},
	}

	payload, err := json.Marshal(requestBody)
	if err != nil {
		return domain.Insight{}, err
	}

	request, err := http.NewRequestWithContext(ctx, http.MethodPost, endpoint, bytes.NewReader(payload))
	if err != nil {
		return domain.Insight{}, err
	}
	request.Header.Set("Authorization", "Bearer "+c.apiKey)
	request.Header.Set("Content-Type", "application/json")

	response, err := c.http.Do(request)
	if err != nil {
		return fallbackInsight(text), err
	}
	defer response.Body.Close()

	var decoded chatResponse
	if err := json.NewDecoder(response.Body).Decode(&decoded); err != nil {
		return fallbackInsight(text), err
	}
	if len(decoded.Choices) == 0 {
		return fallbackInsight(text), errors.New("resposta vazia da Mistral")
	}

	content := strings.TrimSpace(decoded.Choices[0].Message.Content)
	content = strings.TrimPrefix(content, "```json")
	content = strings.TrimPrefix(content, "```")
	content = strings.TrimSuffix(content, "```")

	var insight domain.Insight
	if err := json.Unmarshal([]byte(strings.TrimSpace(content)), &insight); err != nil {
		return fallbackInsight(text), err
	}
	normalizeInsight(&insight)
	return insight, nil
}

func buildPrompt(fileName, text string) string {
	if len(text) > 9000 {
		text = text[:9000]
	}
	return `Analise o documento abaixo.

Arquivo: ` + fileName + `

Retorne JSON exatamente neste formato:
{
  "summary": "resumo executivo em portugues",
  "documentType": "contrato|relatorio|planilha|nota|email|outro",
  "tags": ["tag1", "tag2", "tag3"],
  "entities": ["pessoa ou empresa"],
  "suggestedActions": ["acao pratica"],
  "riskLevel": "baixo|medio|alto"
}

Texto:
` + text
}

func fallbackInsight(text string) domain.Insight {
	summary := text
	if len(summary) > 420 {
		summary = summary[:420] + "..."
	}
	tags := []string{"local", "pendente-ia"}
	if strings.Contains(strings.ToLower(text), "contrato") {
		tags = append(tags, "contrato")
	}
	return domain.Insight{
		Summary:          summary,
		DocumentType:     "outro",
		Tags:             tags,
		Entities:         []string{},
		SuggestedActions: []string{"Revisar o texto extraido", "Rodar analise com a API Mistral ativa"},
		RiskLevel:        "medio",
	}
}

func normalizeInsight(insight *domain.Insight) {
	if insight.Summary == "" {
		insight.Summary = "Sem resumo retornado."
	}
	if insight.DocumentType == "" {
		insight.DocumentType = "outro"
	}
	if insight.RiskLevel == "" {
		insight.RiskLevel = "baixo"
	}
	if len(insight.Tags) == 0 {
		insight.Tags = []string{"sem-tag"}
	}
}

type chatRequest struct {
	Model       string    `json:"model"`
	Messages    []message `json:"messages"`
	Temperature float64   `json:"temperature"`
	MaxTokens   int       `json:"max_tokens"`
}

type message struct {
	Role    string `json:"role"`
	Content string `json:"content"`
}

type chatResponse struct {
	Choices []struct {
		Message message `json:"message"`
	} `json:"choices"`
}
