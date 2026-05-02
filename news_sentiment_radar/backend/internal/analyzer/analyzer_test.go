package analyzer

import "testing"

func TestAnalyzeClassifiesSentimentAndSector(t *testing.T) {
	result := Analyze("Tecnologia cresce com investimento em IA", "Mercado supera expectativas")

	if result.Sentiment != "positivo" {
		t.Fatalf("expected positive sentiment, got %q", result.Sentiment)
	}
	if result.Sector != "tecnologia" {
		t.Fatalf("expected tecnologia sector, got %q", result.Sector)
	}
}

func TestAnalyzeClassifiesNegativeHealthNews(t *testing.T) {
	result := Analyze("Saude em alerta por surto de dengue", "Hospitais registram crise")

	if result.Sentiment != "negativo" {
		t.Fatalf("expected negative sentiment, got %q", result.Sentiment)
	}
	if result.Sector != "saude" {
		t.Fatalf("expected saude sector, got %q", result.Sector)
	}
}
