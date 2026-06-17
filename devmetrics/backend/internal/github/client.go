package github

import (
	"encoding/json"
	"errors"
	"fmt"
	"net/http"
	"time"
)

// ErrNotFound is returned when the requested GitHub resource does not exist.
var ErrNotFound = errors.New("not found")

// ErrRateLimit is returned when the GitHub API rate limit is exceeded.
var ErrRateLimit = errors.New("github API rate limit exceeded — set GITHUB_TOKEN to increase limits")

type User struct {
	Login       string `json:"login"`
	Name        string `json:"name"`
	AvatarURL   string `json:"avatar_url"`
	Bio         string `json:"bio"`
	Company     string `json:"company"`
	Location    string `json:"location"`
	PublicRepos int    `json:"public_repos"`
	Followers   int    `json:"followers"`
	Following   int    `json:"following"`
	CreatedAt   string `json:"created_at"`
	HTMLURL     string `json:"html_url"`
}

type Repository struct {
	Name            string    `json:"name"`
	FullName        string    `json:"full_name"`
	Description     string    `json:"description"`
	StargazersCount int       `json:"stargazers_count"`
	ForksCount      int       `json:"forks_count"`
	Language        string    `json:"language"`
	UpdatedAt       time.Time `json:"updated_at"`
	CreatedAt       time.Time `json:"created_at"`
	HTMLURL         string    `json:"html_url"`
	Fork            bool      `json:"fork"`
	Topics          []string  `json:"topics"`
}

type Client struct {
	httpClient *http.Client
	token      string
	baseURL    string
}

func NewClient(token string) *Client {
	return &Client{
		httpClient: &http.Client{Timeout: 30 * time.Second},
		token:      token,
		baseURL:    "https://api.github.com",
	}
}

func (c *Client) doRequest(url string) (*http.Response, error) {
	req, err := http.NewRequest("GET", url, nil)
	if err != nil {
		return nil, err
	}
	req.Header.Set("Accept", "application/vnd.github.v3+json")
	req.Header.Set("User-Agent", "devmetrics/1.0")
	if c.token != "" {
		req.Header.Set("Authorization", "Bearer "+c.token)
	}
	return c.httpClient.Do(req)
}

func (c *Client) checkStatus(resp *http.Response, context string) error {
	switch resp.StatusCode {
	case http.StatusOK:
		return nil
	case http.StatusNotFound:
		return fmt.Errorf("%w: %s", ErrNotFound, context)
	case http.StatusForbidden, http.StatusTooManyRequests:
		return fmt.Errorf("%w (status %d): %s", ErrRateLimit, resp.StatusCode, context)
	default:
		return fmt.Errorf("github API status %d: %s", resp.StatusCode, context)
	}
}

func (c *Client) GetUser(username string) (*User, error) {
	url := fmt.Sprintf("%s/users/%s", c.baseURL, username)
	resp, err := c.doRequest(url)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	if err := c.checkStatus(resp, "user "+username); err != nil {
		return nil, err
	}
	var user User
	if err := json.NewDecoder(resp.Body).Decode(&user); err != nil {
		return nil, err
	}
	return &user, nil
}

func (c *Client) GetRepos(username string) ([]Repository, error) {
	var allRepos []Repository
	page := 1
	for {
		url := fmt.Sprintf("%s/users/%s/repos?per_page=100&page=%d&sort=updated", c.baseURL, username, page)
		resp, err := c.doRequest(url)
		if err != nil {
			return nil, err
		}
		defer resp.Body.Close()
		if err := c.checkStatus(resp, "repos for "+username); err != nil {
			return nil, err
		}
		var repos []Repository
		if err := json.NewDecoder(resp.Body).Decode(&repos); err != nil {
			return nil, err
		}
		if len(repos) == 0 {
			break
		}
		allRepos = append(allRepos, repos...)
		if len(repos) < 100 {
			break
		}
		page++
	}
	return allRepos, nil
}

func (c *Client) GetRepoLanguages(owner, repo string) (map[string]int, error) {
	url := fmt.Sprintf("%s/repos/%s/%s/languages", c.baseURL, owner, repo)
	resp, err := c.doRequest(url)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	if err := c.checkStatus(resp, fmt.Sprintf("languages for %s/%s", owner, repo)); err != nil {
		return nil, err
	}
	var languages map[string]int
	if err := json.NewDecoder(resp.Body).Decode(&languages); err != nil {
		return nil, err
	}
	return languages, nil
}
