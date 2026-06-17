package service

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"sort"
	"strings"
	"time"

	"fuel-analytics-api/internal/domain"
)

type InsightsService struct {
	apiKey string
	model  string
	client *http.Client
}

type InsightContext struct {
	View        string
	Fuel        string
	State       string
	City        string
	CompareWith string
	StartDate   string
	EndDate     string
	Overview    []domain.FuelSummary
	History     []domain.HistoryPoint
	Forecast    []domain.ForecastPoint
	Comparison  []domain.ComparisonPoint
	Market      []domain.MarketSignal
}

type mistralRequest struct {
	Model          string                   `json:"model"`
	ResponseFormat map[string]any           `json:"response_format"`
	Messages       []map[string]string      `json:"messages"`
	Temperature    float64                  `json:"temperature"`
	MaxTokens      int                      `json:"max_tokens"`
}

type mistralResponse struct {
	Choices []struct {
		Message struct {
			Content json.RawMessage `json:"content"`
		} `json:"message"`
	} `json:"choices"`
}

func NewInsightsService(apiKey, model string) *InsightsService {
	return &InsightsService{
		apiKey: apiKey,
		model:  model,
		client: &http.Client{Timeout: 20 * time.Second},
	}
}

func (s *InsightsService) Build(ctx context.Context, input InsightContext) (domain.InsightPayload, error) {
	if len(input.Overview) == 0 {
		return domain.InsightPayload{
			Title:   "Sem dados suficientes",
			Summary: "O pipeline ainda nao materializou dados para o filtro selecionado.",
			Bullets: []string{"Execute a carga amostral ou a ingestao da ANP."},
			Source:  "rule-based",
		}, nil
	}
	if s.apiKey == "" {
		return s.fallbackInsight(input), nil
	}

	promptData, _ := json.Marshal(map[string]any{
		"view":         input.View,
		"fuel":         input.Fuel,
		"state":        input.State,
		"city":         input.City,
		"compare_with": input.CompareWith,
		"overview":     trimSlice(input.Overview, 8),
		"history":      trimSlice(input.History, 16),
		"forecast":     trimSlice(input.Forecast, 18),
		"comparison":   trimSlice(input.Comparison, 12),
		"market":       trimSlice(input.Market, 12),
	})
	forecastRange := describeForecastRange(input.Forecast)
	requestBody := mistralRequest{
		Model: s.model,
		ResponseFormat: map[string]any{
			"type": "json_object",
		},
		Messages: []map[string]string{
			{
				"role": "system",
				"content": "Voce e um analista de energia e combustiveis. Responda apenas em JSON com os campos title, summary e bullets. bullets deve ser uma lista de no maximo 4 strings, com observacoes acionaveis e sem repetir o summary. Quando houver forecast, trate-o como projecao diaria para datas futuras reais; nao descreva como media semanal e nao inclua datas passadas como horizonte previsto.",
			},
			{
				"role": "user",
				"content": fmt.Sprintf("Gere um briefing para a view=%s com combustivel=%s estado=%s cidade=%s compare_with=%s forecast_range=%s dados=%s. Ajuste o foco conforme a tela: dashboard=panorama, historico=ritmo e mudancas, previsoes=cenario e risco de curto prazo, comparacoes=escolha entre alternativas, combustivel=dossie dedicado.", input.View, input.Fuel, input.State, input.City, input.CompareWith, forecastRange, string(promptData)),
			},
		},
		Temperature: 0.3,
		MaxTokens:   320,
	}
	payload, _ := json.Marshal(requestBody)

	req, err := http.NewRequestWithContext(ctx, http.MethodPost, "https://api.mistral.ai/v1/chat/completions", bytes.NewReader(payload))
	if err != nil {
		return domain.InsightPayload{}, err
	}
	req.Header.Set("Authorization", "Bearer "+s.apiKey)
	req.Header.Set("Content-Type", "application/json")

	resp, err := s.client.Do(req)
	if err != nil {
		return s.fallbackInsight(input), nil
	}
	defer resp.Body.Close()
	if resp.StatusCode >= http.StatusBadRequest {
		return s.fallbackInsight(input), nil
	}

	var decoded mistralResponse
	if err := json.NewDecoder(resp.Body).Decode(&decoded); err != nil || len(decoded.Choices) == 0 {
		return s.fallbackInsight(input), nil
	}

	content, err := decodeMistralContent(decoded.Choices[0].Message.Content)
	if err != nil {
		return s.fallbackInsight(input), nil
	}
	var insight domain.InsightPayload
	if err := json.Unmarshal([]byte(content), &insight); err != nil {
		return s.fallbackInsight(input), nil
	}
	insight.Source = "mistral"
	return insight, nil
}

func (s *InsightsService) fallbackInsight(input InsightContext) domain.InsightPayload {
	top := input.Overview[0]
	viewTitle := map[string]string{
		"dashboard":   "Panorama executivo",
		"historico":   "Leitura historica",
		"previsoes":   "Leitura de cenarios",
		"comparacoes": "Duelo entre combustiveis",
		"combustivel": "Dossie do combustivel",
	}[input.View]
	if viewTitle == "" {
		viewTitle = "Panorama analitico"
	}

	bullets := []string{
		fmt.Sprintf("Preco medio atual em %s: R$ %.2f", top.State, top.AveragePrice),
		fmt.Sprintf("Direcao mais recente: %s", top.PriceDirection),
	}
	if len(input.Market) > 0 {
		latestMarket := input.Market[len(input.Market)-1]
		bullets = append(bullets, fmt.Sprintf("Regime de mercado: %s", latestMarket.MarketRegime))
	}
	if len(input.Forecast) > 0 {
		latestForecast := input.Forecast[len(input.Forecast)-1]
		bullets = append(bullets, fmt.Sprintf("Projecao final do horizonte em %s: R$ %.2f", latestForecast.Week, latestForecast.Predicted))
	}

	return domain.InsightPayload{
		Title:   fmt.Sprintf("%s de %s em %s", viewTitle, strings.ToUpper(input.Fuel), strings.ToUpper(input.State)),
		Summary: fmt.Sprintf("Preco medio atual em %s: R$ %.2f com volatilidade %.3f. O fallback local sintetiza historico, mercado e previsao mesmo sem resposta da Mistral.", top.State, top.AveragePrice, top.Volatility),
		Bullets: bullets,
		Source: "rule-based",
	}
}

func describeForecastRange(items []domain.ForecastPoint) string {
	if len(items) == 0 {
		return "sem horizonte previsto"
	}
	points := append([]domain.ForecastPoint(nil), items...)
	sort.Slice(points, func(i, j int) bool {
		return points[i].Week < points[j].Week
	})
	return fmt.Sprintf("%s ate %s", points[0].Week, points[len(points)-1].Week)
}

func trimSlice[T any](items []T, limit int) []T {
	if len(items) <= limit {
		return items
	}
	return items[len(items)-limit:]
}

func decodeMistralContent(raw json.RawMessage) (string, error) {
	var text string
	if err := json.Unmarshal(raw, &text); err == nil {
		return text, nil
	}

	var chunks []struct {
		Type string `json:"type"`
		Text string `json:"text"`
	}
	if err := json.Unmarshal(raw, &chunks); err != nil {
		return "", err
	}

	var builder strings.Builder
	for _, chunk := range chunks {
		if chunk.Type == "text" {
			builder.WriteString(chunk.Text)
		}
	}
	if builder.Len() == 0 {
		return "", io.EOF
	}
	return builder.String(), nil
}
