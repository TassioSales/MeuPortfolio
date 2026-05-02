package news

import (
	"context"
	"crypto/sha1"
	"encoding/hex"
	"encoding/xml"
	"io"
	"net/http"
	"strings"
	"time"

	"newssentiment/backend/internal/analyzer"
)

type rssFeed struct {
	Channel struct {
		Items []rssItem `xml:"item"`
	} `xml:"channel"`
}

type rssItem struct {
	Title       string `xml:"title"`
	Description string `xml:"description"`
	Link        string `xml:"link"`
	PubDate     string `xml:"pubDate"`
	GUID        string `xml:"guid"`
}

type atomFeed struct {
	Entries []atomEntry `xml:"entry"`
}

type atomEntry struct {
	Title   string     `xml:"title"`
	Summary string     `xml:"summary"`
	Content string     `xml:"content"`
	Links   []atomLink `xml:"link"`
	Updated string     `xml:"updated"`
	ID      string     `xml:"id"`
}

type atomLink struct {
	Href string `xml:"href,attr"`
}

func FetchArticles(ctx context.Context, source Source) ([]Article, error) {
	request, err := http.NewRequestWithContext(ctx, http.MethodGet, source.URL, nil)
	if err != nil {
		return nil, err
	}
	request.Header.Set("User-Agent", "NewsSentimentRadar/1.0")

	response, err := http.DefaultClient.Do(request)
	if err != nil {
		return nil, err
	}
	defer response.Body.Close()

	body, err := io.ReadAll(io.LimitReader(response.Body, 2_000_000))
	if err != nil {
		return nil, err
	}

	if strings.Contains(string(body[:min(len(body), 200)]), "<feed") {
		return parseAtom(body, source)
	}
	return parseRSS(body, source)
}

func parseRSS(body []byte, source Source) ([]Article, error) {
	var feed rssFeed
	if err := xml.Unmarshal(body, &feed); err != nil {
		return nil, err
	}

	articles := make([]Article, 0, len(feed.Channel.Items))
	for _, item := range feed.Channel.Items {
		title := cleanText(item.Title)
		description := cleanText(item.Description)
		result := analyzer.Analyze(title, description)
		if result.Sector == "geral" && source.Sector != "" {
			result.Sector = source.Sector
		}
		articles = append(articles, Article{
			ID:          stableID(item.GUID + item.Link + title),
			Title:       title,
			Description: description,
			Link:        strings.TrimSpace(item.Link),
			Source:      source.Name,
			PublishedAt: parseTime(item.PubDate),
			Sentiment:   result.Sentiment,
			Score:       result.Score,
			Sector:      result.Sector,
			Entities:    result.Entities,
		})
	}
	return articles, nil
}

func parseAtom(body []byte, source Source) ([]Article, error) {
	var feed atomFeed
	if err := xml.Unmarshal(body, &feed); err != nil {
		return nil, err
	}

	articles := make([]Article, 0, len(feed.Entries))
	for _, entry := range feed.Entries {
		link := ""
		if len(entry.Links) > 0 {
			link = entry.Links[0].Href
		}
		description := entry.Summary
		if description == "" {
			description = entry.Content
		}
		title := cleanText(entry.Title)
		description = cleanText(description)
		result := analyzer.Analyze(title, description)
		if result.Sector == "geral" && source.Sector != "" {
			result.Sector = source.Sector
		}
		articles = append(articles, Article{
			ID:          stableID(entry.ID + link + title),
			Title:       title,
			Description: description,
			Link:        strings.TrimSpace(link),
			Source:      source.Name,
			PublishedAt: parseTime(entry.Updated),
			Sentiment:   result.Sentiment,
			Score:       result.Score,
			Sector:      result.Sector,
			Entities:    result.Entities,
		})
	}
	return articles, nil
}

func cleanText(value string) string {
	replacer := strings.NewReplacer("<![CDATA[", "", "]]>", "", "\n", " ", "\t", " ")
	value = replacer.Replace(value)
	value = htmlTagPattern.ReplaceAllString(value, "")
	return strings.TrimSpace(value)
}

func stableID(value string) string {
	hash := sha1.Sum([]byte(value))
	return hex.EncodeToString(hash[:])
}

func parseTime(value string) time.Time {
	value = strings.TrimSpace(value)
	layouts := []string{time.RFC1123Z, time.RFC1123, time.RFC3339, "Mon, 02 Jan 2006 15:04:05 -0700"}
	for _, layout := range layouts {
		if parsed, err := time.Parse(layout, value); err == nil {
			return parsed.UTC()
		}
	}
	return time.Now().UTC()
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}
