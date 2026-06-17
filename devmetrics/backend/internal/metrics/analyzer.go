package metrics

import (
	"sort"
	"time"

	"devmetrics/backend/internal/github"
)

type LanguageStat struct {
	Language   string  `json:"language"`
	Bytes      int     `json:"bytes"`
	Percentage float64 `json:"percentage"`
}

type RepoSummary struct {
	Name        string    `json:"name"`
	Description string    `json:"description"`
	Stars       int       `json:"stars"`
	Forks       int       `json:"forks"`
	Language    string    `json:"language"`
	UpdatedAt   time.Time `json:"updated_at"`
	HTMLURL     string    `json:"html_url"`
	Topics      []string  `json:"topics"`
}

type YearlyActivity struct {
	Year  int `json:"year"`
	Count int `json:"count"`
}

type Metrics struct {
	TotalRepos   int              `json:"total_repos"`
	TotalStars   int              `json:"total_stars"`
	TotalForks   int              `json:"total_forks"`
	Languages    []LanguageStat   `json:"languages"`
	TopRepos     []RepoSummary    `json:"top_repos"`
	ReposByYear  []YearlyActivity `json:"repos_by_year"`
	MostUsedLang string           `json:"most_used_language"`
}

type Analyzer struct{}

func NewAnalyzer() *Analyzer {
	return &Analyzer{}
}

func (a *Analyzer) Compute(repos []github.Repository, langData map[string]int) *Metrics {
	m := &Metrics{}

	for _, r := range repos {
		m.TotalRepos++
		m.TotalStars += r.StargazersCount
		m.TotalForks += r.ForksCount
	}

	// Language distribution
	if len(langData) > 0 {
		totalBytes := 0
		for _, b := range langData {
			totalBytes += b
		}
		var langStats []LanguageStat
		for lang, bytes := range langData {
			pct := 0.0
			if totalBytes > 0 {
				pct = float64(bytes) / float64(totalBytes) * 100
			}
			langStats = append(langStats, LanguageStat{Language: lang, Bytes: bytes, Percentage: pct})
		}
		sort.Slice(langStats, func(i, j int) bool {
			return langStats[i].Bytes > langStats[j].Bytes
		})
		if len(langStats) > 10 {
			langStats = langStats[:10]
		}
		m.Languages = langStats
		if len(langStats) > 0 {
			m.MostUsedLang = langStats[0].Language
		}
	}

	// Top repos by stars
	topRepos := make([]github.Repository, len(repos))
	copy(topRepos, repos)
	sort.Slice(topRepos, func(i, j int) bool {
		return topRepos[i].StargazersCount > topRepos[j].StargazersCount
	})
	if len(topRepos) > 6 {
		topRepos = topRepos[:6]
	}
	for _, r := range topRepos {
		m.TopRepos = append(m.TopRepos, RepoSummary{
			Name:        r.Name,
			Description: r.Description,
			Stars:       r.StargazersCount,
			Forks:       r.ForksCount,
			Language:    r.Language,
			UpdatedAt:   r.UpdatedAt,
			HTMLURL:     r.HTMLURL,
			Topics:      r.Topics,
		})
	}

	// Repos by year
	yearMap := map[int]int{}
	for _, r := range repos {
		year := r.CreatedAt.Year()
		yearMap[year]++
	}
	var years []int
	for y := range yearMap {
		years = append(years, y)
	}
	sort.Ints(years)
	for _, y := range years {
		m.ReposByYear = append(m.ReposByYear, YearlyActivity{Year: y, Count: yearMap[y]})
	}

	return m
}

// AggregateLanguages merges multiple language maps
func AggregateLanguages(langMaps []map[string]int) map[string]int {
	result := map[string]int{}
	for _, lm := range langMaps {
		for lang, bytes := range lm {
			result[lang] += bytes
		}
	}
	return result
}
