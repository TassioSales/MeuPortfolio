package study

import (
	"fmt"
	"regexp"
	"sort"
	"strings"
	"time"

	"documind/backend/internal/domain"
)

var wordPattern = regexp.MustCompile(`[A-Za-zÀ-ÿ0-9]{4,}`)

// BuildPlan turns extracted text into a practical spaced-repetition study plan.
// It is deterministic and local, so the user still gets useful study structure
// when the AI API is unavailable.
func BuildPlan(fileName, text string, insight domain.Insight, now time.Time) domain.StudyPlan {
	clean := normalizeText(text)
	topics := buildTopics(clean, insight)
	cards := buildFlashcards(clean, topics, now)
	schedule := buildSchedule(topics, now)

	plan := domain.StudyPlan{
		Title:            studyTitle(fileName, insight),
		EstimatedMinutes: estimateMinutes(clean, len(cards)),
		Objectives:       buildObjectives(topics),
		Topics:           topics,
		Schedule:         schedule,
		Flashcards:       cards,
	}
	plan.Progress = Progress(plan, now)
	return plan
}

func Review(plan domain.StudyPlan, cardID, result string, now time.Time) domain.StudyPlan {
	for index := range plan.Flashcards {
		card := &plan.Flashcards[index]
		if card.ID != cardID {
			continue
		}
		card.Reviews++
		card.LastReviewed = &now
		switch result {
		case "again":
			card.IntervalDays = 1
			card.Ease = max(130, card.Ease-20)
			card.Status = "rever"
		case "hard":
			card.IntervalDays = max(1, card.IntervalDays)
			card.Ease = max(130, card.Ease-10)
			card.Status = "dificil"
		default:
			card.IntervalDays = nextInterval(card.IntervalDays, card.Ease)
			card.Ease = min(260, card.Ease+8)
			card.Status = "aprendido"
		}
		card.DueDate = now.AddDate(0, 0, card.IntervalDays)
		break
	}
	plan.Progress = Progress(plan, now)
	return plan
}

func Progress(plan domain.StudyPlan, now time.Time) domain.StudyProgress {
	progress := domain.StudyProgress{
		TotalCards:       len(plan.Flashcards),
		EstimatedMinutes: plan.EstimatedMinutes,
	}
	var next *time.Time
	for _, card := range plan.Flashcards {
		if card.Reviews > 0 {
			progress.ReviewedCards++
		}
		if !card.DueDate.After(now) {
			progress.DueCards++
		}
		if next == nil || card.DueDate.Before(*next) {
			value := card.DueDate
			next = &value
		}
	}
	if progress.TotalCards > 0 {
		progress.Completion = int(float64(progress.ReviewedCards) / float64(progress.TotalCards) * 100)
	}
	progress.NextReview = next
	return progress
}

func buildTopics(text string, insight domain.Insight) []domain.StudyTopic {
	seen := map[string]bool{}
	topics := []domain.StudyTopic{}
	for _, tag := range insight.Tags {
		name := strings.TrimSpace(tag)
		if name == "" || seen[strings.ToLower(name)] {
			continue
		}
		seen[strings.ToLower(name)] = true
		topics = append(topics, domain.StudyTopic{Name: titleCase(name), Summary: "Revisar conceitos, definicoes e exemplos ligados a " + name + ".", Priority: "alta"})
		if len(topics) == 5 {
			break
		}
	}

	for _, keyword := range topKeywords(text, 8) {
		if seen[strings.ToLower(keyword)] {
			continue
		}
		seen[strings.ToLower(keyword)] = true
		topics = append(topics, domain.StudyTopic{Name: titleCase(keyword), Summary: "Identificar onde aparece no material e montar exemplos de aplicacao.", Priority: priority(len(topics))})
		if len(topics) == 6 {
			break
		}
	}

	if len(topics) == 0 {
		topics = append(topics, domain.StudyTopic{Name: "Leitura guiada", Summary: "Ler o material em blocos, separar duvidas e revisar os pontos principais.", Priority: "alta"})
	}
	return topics
}

func buildFlashcards(text string, topics []domain.StudyTopic, now time.Time) []domain.Flashcard {
	sentences := importantSentences(text, 12)
	cards := []domain.Flashcard{}
	for index, topic := range topics {
		answer := topic.Summary
		if index < len(sentences) {
			answer = sentences[index]
		}
		cards = append(cards, domain.Flashcard{
			ID:           fmt.Sprintf("card-%02d", len(cards)+1),
			Question:     "Explique o conceito de " + topic.Name + " com suas palavras.",
			Answer:       answer,
			DueDate:      now,
			IntervalDays: 1,
			Ease:         220,
			Status:       "novo",
		})
	}
	for len(cards) < 8 && len(sentences) > len(cards) {
		sentence := sentences[len(cards)]
		cards = append(cards, domain.Flashcard{
			ID:           fmt.Sprintf("card-%02d", len(cards)+1),
			Question:     "Qual e a ideia central deste trecho?",
			Answer:       sentence,
			DueDate:      now.AddDate(0, 0, len(cards)%2),
			IntervalDays: 1,
			Ease:         220,
			Status:       "novo",
		})
	}
	return cards
}

func buildSchedule(topics []domain.StudyTopic, now time.Time) []domain.StudySession {
	steps := []struct {
		day   int
		title string
	}{
		{0, "Diagnostico e leitura ativa"},
		{1, "Revisao 1: recordacao curta"},
		{3, "Revisao 2: exercicios e lacunas"},
		{7, "Revisao 3: consolidacao"},
		{14, "Revisao final: simulado"},
	}
	sessions := make([]domain.StudySession, 0, len(steps))
	for index, step := range steps {
		title := step.title
		if index < len(topics) {
			title = title + " - " + topics[index].Name
		}
		sessions = append(sessions, domain.StudySession{
			ID:              fmt.Sprintf("session-%02d", index+1),
			Title:           title,
			DueDate:         now.AddDate(0, 0, step.day),
			DurationMinutes: 25 + index*5,
			Status:          "pendente",
		})
	}
	return sessions
}

func buildObjectives(topics []domain.StudyTopic) []string {
	objectives := []string{"Criar um mapa mental do material", "Responder flashcards sem consultar o texto", "Revisar nos intervalos programados"}
	for _, topic := range topics[:min(len(topics), 3)] {
		objectives = append(objectives, "Dominar: "+topic.Name)
	}
	return objectives
}

func importantSentences(text string, limit int) []string {
	raw := regexp.MustCompile(`[.!?]\s+`).Split(text, -1)
	sentences := []string{}
	for _, sentence := range raw {
		sentence = strings.TrimSpace(sentence)
		if len([]rune(sentence)) < 45 || len([]rune(sentence)) > 260 {
			continue
		}
		sentences = append(sentences, sentence)
		if len(sentences) == limit {
			break
		}
	}
	return sentences
}

func topKeywords(text string, limit int) []string {
	stop := map[string]bool{"para": true, "como": true, "mais": true, "este": true, "esta": true, "pela": true, "pelo": true, "entre": true, "sobre": true, "quando": true, "onde": true, "tambem": true, "documento": true, "arquivo": true, "texto": true}
	counts := map[string]int{}
	for _, word := range wordPattern.FindAllString(strings.ToLower(text), -1) {
		if stop[word] {
			continue
		}
		counts[word]++
	}
	type pair struct {
		word  string
		count int
	}
	pairs := []pair{}
	for word, count := range counts {
		pairs = append(pairs, pair{word: word, count: count})
	}
	sort.Slice(pairs, func(i, j int) bool { return pairs[i].count > pairs[j].count })
	words := []string{}
	for _, pair := range pairs {
		words = append(words, pair.word)
		if len(words) == limit {
			break
		}
	}
	return words
}

func normalizeText(text string) string {
	text = strings.ReplaceAll(text, "\x00", " ")
	text = regexp.MustCompile(`\s+`).ReplaceAllString(text, " ")
	return strings.TrimSpace(text)
}

func studyTitle(fileName string, insight domain.Insight) string {
	if insight.DocumentType != "" && insight.DocumentType != "outro" {
		return "Plano de estudo: " + insight.DocumentType
	}
	return "Plano de estudo: " + fileName
}

func estimateMinutes(text string, cards int) int {
	words := len(strings.Fields(text))
	minutes := words/180 + cards*3
	return min(max(minutes, 25), 180)
}

func nextInterval(current, ease int) int {
	if current <= 1 {
		return 3
	}
	return min(45, max(2, current*ease/100))
}

func titleCase(value string) string {
	value = strings.TrimSpace(value)
	if value == "" {
		return value
	}
	return strings.ToUpper(value[:1]) + value[1:]
}

func priority(index int) string {
	if index < 2 {
		return "alta"
	}
	if index < 4 {
		return "media"
	}
	return "baixa"
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}

func max(a, b int) int {
	if a > b {
		return a
	}
	return b
}
