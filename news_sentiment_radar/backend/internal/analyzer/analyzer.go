package analyzer

import (
	"regexp"
	"sort"
	"strings"
	"unicode"
)

type Result struct {
	Sentiment string   `json:"sentiment"`
	Score     int      `json:"score"`
	Sector    string   `json:"sector"`
	Entities  []string `json:"entities"`
}

var positiveWords = []string{
	"alta", "avanço", "cresce", "crescimento", "melhora", "recorde", "aprova", "aprovado",
	"lucro", "ganha", "recupera", "inovação", "investimento", "expande", "queda da inflação",
	"supera", "reduz", "acordo", "vacina", "cura",
}

var negativeWords = []string{
	"queda", "cai", "crise", "risco", "alerta", "morte", "mortes", "ataque", "guerra",
	"prejuízo", "perda", "investigação", "denúncia", "fraude", "inflação", "juros altos",
	"demissão", "corte", "bloqueio", "doença", "surto", "colapso",
}

var sectorKeywords = map[string][]string{
	"economia": {
		"economia", "mercado", "inflação", "juros", "dólar", "bolsa", "pib", "banco",
		"preço", "combustível", "imposto", "fazenda", "selic", "crédito",
	},
	"politica": {
		"governo", "congresso", "senado", "câmara", "presidente", "ministro", "eleição",
		"partido", "stf", "política", "votação", "prefeito", "governador",
	},
	"tecnologia": {
		"tecnologia", "ia", "inteligência artificial", "startup", "software", "dados",
		"app", "internet", "chip", "big tech", "segurança digital",
	},
	"saude": {
		"saúde", "hospital", "vacina", "médico", "doença", "dengue", "covid",
		"ans", "sus", "medicamento", "epidemia", "surto",
	},
}

var entityPattern = regexp.MustCompile(`\b([A-ZÁÀÂÃÉÊÍÓÔÕÚÇ][\p{L}0-9]+(?:\s+(?:de|da|do|dos|das|e|[A-ZÁÀÂÃÉÊÍÓÔÕÚÇ][\p{L}0-9]+)){0,3})\b`)
var wordPattern = regexp.MustCompile(`[\p{L}0-9]+`)

func Analyze(title, description string) Result {
	text := normalize(title + " " + description)
	score := sentimentScore(text)

	sentiment := "neutro"
	if score > 0 {
		sentiment = "positivo"
	}
	if score < 0 {
		sentiment = "negativo"
	}

	return Result{
		Sentiment: sentiment,
		Score:     score,
		Sector:    classifySector(text),
		Entities:  extractEntities(title + " " + description),
	}
}

func sentimentScore(text string) int {
	score := 0
	for _, word := range positiveWords {
		if containsTerm(text, word) {
			score++
		}
	}
	for _, word := range negativeWords {
		if containsTerm(text, word) {
			score--
		}
	}
	return score
}

func classifySector(text string) string {
	type match struct {
		sector string
		count  int
	}

	matches := []match{}
	for sector, keywords := range sectorKeywords {
		count := 0
		for _, keyword := range keywords {
			if containsTerm(text, keyword) {
				count++
			}
		}
		matches = append(matches, match{sector: sector, count: count})
	}

	sort.SliceStable(matches, func(i, j int) bool {
		return matches[i].count > matches[j].count
	})

	if len(matches) == 0 || matches[0].count == 0 {
		return "geral"
	}
	return matches[0].sector
}

func extractEntities(text string) []string {
	seen := map[string]bool{}
	entities := []string{}
	for _, match := range entityPattern.FindAllString(text, -1) {
		cleaned := strings.TrimSpace(match)
		if len([]rune(cleaned)) < 4 || isIgnoredEntity(cleaned) || seen[cleaned] {
			continue
		}
		seen[cleaned] = true
		entities = append(entities, cleaned)
		if len(entities) == 8 {
			break
		}
	}
	return entities
}

func isIgnoredEntity(value string) bool {
	lower := strings.ToLower(value)
	ignored := map[string]bool{
		"rss": true, "http": true, "https": true,
		"assista": true, "clique": true, "segundo": true, "siga": true,
		"participe": true, "participe do": true, "divulgação": true, "vídeos": true,
		"whatsapp": true, "publicidade": true, "arquivo": true, "reprodução": true,
		"como": true, "também": true, "novo": true, "novas": true, "esperando": true,
		"brasil": false,
	}
	return ignored[lower]
}

func containsTerm(text, term string) bool {
	term = normalize(term)
	if strings.Contains(term, " ") || len([]rune(term)) > 3 {
		return strings.Contains(text, term)
	}

	for _, word := range wordPattern.FindAllString(text, -1) {
		if word == term {
			return true
		}
	}
	return false
}

func normalize(value string) string {
	return strings.ToLower(strings.Map(func(r rune) rune {
		if unicode.IsControl(r) {
			return ' '
		}
		return r
	}, value))
}
