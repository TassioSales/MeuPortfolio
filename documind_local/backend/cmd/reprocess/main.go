package main

import (
	"context"
	"log"
	"path/filepath"
	"time"

	"documind/backend/internal/ai"
	"documind/backend/internal/config"
	"documind/backend/internal/domain"
	"documind/backend/internal/extract"
	"documind/backend/internal/store"
)

func main() {
	cfg := config.Load()
	documentStore, err := store.New(filepath.Join(cfg.StorageDir, "db.json"))
	if err != nil {
		log.Fatalf("store init failed: %v", err)
	}
	client := ai.NewClient(cfg.MistralKey, cfg.MistralModel)

	for _, document := range documentStore.All() {
		path := filepath.Join(cfg.StorageDir, "uploads", document.StoredName)
		text, err := extract.TextFromPath(path, document.FileName)
		if err != nil {
			log.Printf("extract failed %s: %v", document.FileName, err)
			continue
		}

		document.Text = text
		document.Preview = preview(text)
		document.Insight = analyze(client, document)
		document.AnalyzedAt = time.Now().UTC()
		if err := documentStore.Update(document); err != nil {
			log.Printf("update failed %s: %v", document.FileName, err)
			continue
		}
		log.Printf("reprocessed %s (%d chars)", document.FileName, len(text))
	}
}

func analyze(client *ai.Client, document domain.Document) domain.Insight {
	ctx, cancel := context.WithTimeout(context.Background(), 40*time.Second)
	defer cancel()
	insight, err := client.Analyze(ctx, document.FileName, document.Text)
	if err != nil {
		log.Printf("analysis fallback %s: %v", document.FileName, err)
	}
	return insight
}

func preview(text string) string {
	if len(text) > 360 {
		return text[:360] + "..."
	}
	return text
}
