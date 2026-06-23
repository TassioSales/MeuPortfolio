package repository

import (
	"context"
	"encoding/json"
	"fmt"
	"math"
	"os"
	"sort"
	"strings"

	"fuel-analytics-api/internal/domain"
)

type AnalyticsRepository struct {
	overview  []domain.FuelSummary
	history   []domain.HistoryPoint
	fuels     []string
	explorer  domain.ExplorerPayload
	forecasts map[string][]domain.ForecastPoint
	market    []domain.MarketSignal
}

func NewAnalyticsRepository(
	overviewPath,
	historyPath,
	fuelsPath,
	explorerPath,
	forecastPath,
	marketPath string,
) (*AnalyticsRepository, error) {
	overview, err := loadOverview(overviewPath)
	if err != nil {
		return nil, err
	}
	history, err := loadHistory(historyPath)
	if err != nil {
		return nil, err
	}
	fuels, err := loadFuels(fuelsPath)
	if err != nil {
		return nil, err
	}
	explorer, err := loadExplorer(explorerPath)
	if err != nil {
		return nil, err
	}
	forecasts, err := loadForecasts(forecastPath)
	if err != nil {
		return nil, err
	}
	market, err := loadMarket(marketPath)
	if err != nil {
		return nil, err
	}
	return &AnalyticsRepository{
		overview:  overview,
		history:   history,
		fuels:     fuels,
		explorer:  explorer,
		forecasts: forecasts,
		market:    market,
	}, nil
}

func loadOverview(path string) ([]domain.FuelSummary, error) {
	var result []domain.FuelSummary
	return result, loadJSON(path, &result)
}

func loadHistory(path string) ([]domain.HistoryPoint, error) {
	var result []domain.HistoryPoint
	return result, loadJSON(path, &result)
}

func loadFuels(path string) ([]string, error) {
	var result []string
	return result, loadJSON(path, &result)
}

func loadExplorer(path string) (domain.ExplorerPayload, error) {
	var result domain.ExplorerPayload
	return result, loadJSON(path, &result)
}

func loadForecasts(path string) (map[string][]domain.ForecastPoint, error) {
	result := map[string][]domain.ForecastPoint{}
	return result, loadJSON(path, &result)
}

func loadMarket(path string) ([]domain.MarketSignal, error) {
	var result []domain.MarketSignal
	return result, loadJSON(path, &result)
}

func loadJSON(path string, target any) error {
	payload, err := os.ReadFile(path)
	if err != nil {
		return err
	}
	return json.Unmarshal(payload, target)
}

func (r *AnalyticsRepository) Health(_ context.Context) error {
	if len(r.history) == 0 || len(r.overview) == 0 {
		return fmt.Errorf("repository snapshots not loaded")
	}
	return nil
}

func (r *AnalyticsRepository) Fuels(_ context.Context) ([]string, error) {
	return append([]string(nil), r.fuels...), nil
}

func (r *AnalyticsRepository) Overview(_ context.Context, fuel, state, startDate, endDate string) ([]domain.FuelSummary, error) {
	filteredFuel := strings.ToLower(fuel)
	filteredState := strings.ToUpper(state)
	type aggregate struct {
		count        float64
		totalPrice   float64
		totalVol     float64
		firstPrice   float64
		lastPrice    float64
		firstWeek    string
		lastWeek     string
		state        string
		product      string
		volRef       domain.FuelSummary
	}
	seed := map[string]domain.FuelSummary{}
	for _, item := range r.overview {
		seed[item.Product+":"+item.State] = item
	}
	byState := map[string]*aggregate{}
	for _, item := range r.history {
		if filteredFuel != "" && item.Product != filteredFuel {
			continue
		}
		if filteredState != "" && item.State != filteredState {
			continue
		}
		if startDate != "" && item.Week < startDate {
			continue
		}
		if endDate != "" && item.Week > endDate {
			continue
		}
		key := item.Product + ":" + item.State
		entry, ok := byState[key]
		if !ok {
			entry = &aggregate{
				state:    item.State,
				product:  item.Product,
				firstWeek: item.Week,
				lastWeek:  item.Week,
				firstPrice: item.AveragePrice,
				lastPrice:  item.AveragePrice,
				volRef:   seed[key],
			}
			byState[key] = entry
		}
		entry.count += 1
		entry.totalPrice += item.AveragePrice
		entry.totalVol += item.Volatility
		if item.Week < entry.firstWeek {
			entry.firstWeek = item.Week
			entry.firstPrice = item.AveragePrice
		}
		if item.Week >= entry.lastWeek {
			entry.lastWeek = item.Week
			entry.lastPrice = item.AveragePrice
		}
	}

	result := make([]domain.FuelSummary, 0, len(byState))
	for _, item := range byState {
		if item.count == 0 {
			continue
		}
		direction := "flat"
		if item.lastPrice > item.firstPrice+0.01 {
			direction = "up"
		} else if item.lastPrice < item.firstPrice-0.01 {
			direction = "down"
		}
		result = append(result, domain.FuelSummary{
			Product:        item.product,
			State:          item.state,
			AveragePrice:   item.totalPrice / item.count,
			Volatility:     item.totalVol / item.count,
			Dollar:         item.volRef.Dollar,
			Brent:          item.volRef.Brent,
			IPCA:           item.volRef.IPCA,
			PriceDirection: direction,
		})
	}
	sort.Slice(result, func(i, j int) bool { return result[i].AveragePrice > result[j].AveragePrice })
	return result, nil
}

func (r *AnalyticsRepository) History(_ context.Context, fuel, state, city, startDate, endDate string) ([]domain.HistoryPoint, error) {
	filteredFuel := strings.ToLower(fuel)
	filteredState := strings.ToUpper(state)
	filteredCity := strings.TrimSpace(city)
	var result []domain.HistoryPoint
	if filteredCity == "" {
		type aggregate struct {
			Count        float64
			AveragePrice float64
			Volatility   float64
			AverageBuy   float64
		}
		byWeek := map[string]*aggregate{}
		for _, item := range r.history {
			if filteredFuel != "" && item.Product != filteredFuel {
				continue
			}
			if filteredState != "" && item.State != filteredState {
				continue
			}
			if startDate != "" && item.Week < startDate {
				continue
			}
			if endDate != "" && item.Week > endDate {
				continue
			}
			entry, ok := byWeek[item.Week]
			if !ok {
				entry = &aggregate{}
				byWeek[item.Week] = entry
			}
			entry.Count += 1
			entry.AveragePrice += item.AveragePrice
			entry.Volatility += item.Volatility
			entry.AverageBuy += item.AverageBuy
		}
		for week, item := range byWeek {
			if item.Count == 0 {
				continue
			}
			result = append(result, domain.HistoryPoint{
				Week:         week,
				State:        filteredState,
				City:         "",
				Product:      filteredFuel,
				AveragePrice: item.AveragePrice / item.Count,
				Volatility:   item.Volatility / item.Count,
				AverageBuy:   item.AverageBuy / item.Count,
			})
		}
		sort.Slice(result, func(i, j int) bool {
			return result[i].Week < result[j].Week
		})
		return result, nil
	}
	for _, item := range r.history {
		if filteredFuel != "" && item.Product != filteredFuel {
			continue
		}
		if filteredState != "" && item.State != filteredState {
			continue
		}
		if filteredCity != "" && !strings.EqualFold(item.City, filteredCity) {
			continue
		}
		if startDate != "" && item.Week < startDate {
			continue
		}
		if endDate != "" && item.Week > endDate {
			continue
		}
		result = append(result, item)
	}
	sort.Slice(result, func(i, j int) bool {
		return result[i].Week < result[j].Week
	})
	return result, nil
}

func (r *AnalyticsRepository) Map(_ context.Context, fuel string) ([]domain.FuelSummary, error) {
	return r.Overview(context.Background(), fuel, "", "", "")
}

func (r *AnalyticsRepository) Compare(ctx context.Context, fuel, compareWith, state, startDate, endDate string) ([]domain.ComparisonPoint, error) {
	primary, err := r.History(ctx, fuel, state, "", startDate, endDate)
	if err != nil {
		return nil, err
	}
	secondary, err := r.History(ctx, compareWith, state, "", startDate, endDate)
	if err != nil {
		return nil, err
	}
	secondaryByWeek := map[string]domain.HistoryPoint{}
	for _, item := range secondary {
		secondaryByWeek[item.Week] = item
	}
	var result []domain.ComparisonPoint
	for _, item := range primary {
		other, ok := secondaryByWeek[item.Week]
		if !ok {
			continue
		}
		recommended := fuel
		if compareWith == "etanol" && other.AveragePrice <= item.AveragePrice*0.7 {
			recommended = "etanol"
		}
		result = append(result, domain.ComparisonPoint{
			Week:             item.Week,
			PrimaryFuel:      fuel,
			ComparedFuel:     compareWith,
			PrimaryPrice:     item.AveragePrice,
			ComparedPrice:    other.AveragePrice,
			AdvantagePercent: round(((other.AveragePrice / item.AveragePrice) - 1) * 100.0),
			RecommendedFuel:  recommended,
		})
	}
	return result, nil
}

func (r *AnalyticsRepository) Forecast(_ context.Context, fuel, state, startDate, endDate string) ([]domain.ForecastPoint, error) {
	key := fmt.Sprintf("%s:%s", strings.ToLower(fuel), strings.ToUpper(state))
	if items, ok := r.forecasts[key]; ok {
		sort.Slice(items, func(i, j int) bool {
			return items[i].Week < items[j].Week
		})
		return items, nil
	}
	return []domain.ForecastPoint{}, nil
}

func (r *AnalyticsRepository) Market(_ context.Context, fuel, state, startDate, endDate string) ([]domain.MarketSignal, error) {
	filteredFuel := strings.ToLower(fuel)
	filteredState := strings.ToUpper(state)
	var result []domain.MarketSignal
	for _, item := range r.market {
		if filteredFuel != "" && item.Product != filteredFuel {
			continue
		}
		if filteredState != "" && item.State != filteredState {
			continue
		}
		if startDate != "" && item.Month < startDate[:7]+"-01" {
			continue
		}
		if endDate != "" && item.Month > endDate[:7]+"-31" {
			continue
		}
		result = append(result, item)
	}
	sort.Slice(result, func(i, j int) bool {
		return result[i].Month < result[j].Month
	})
	return result, nil
}

func (r *AnalyticsRepository) Explorer(_ context.Context) (domain.ExplorerPayload, error) {
	return r.explorer, nil
}

func (r *AnalyticsRepository) Cities(_ context.Context, fuel, state string) ([]string, error) {
	filteredFuel := strings.ToLower(fuel)
	filteredState := strings.ToUpper(state)
	set := map[string]struct{}{}
	for _, item := range r.history {
		if filteredFuel != "" && item.Product != filteredFuel {
			continue
		}
		if filteredState != "" && item.State != filteredState {
			continue
		}
		if strings.TrimSpace(item.City) == "" {
			continue
		}
		set[item.City] = struct{}{}
	}
	result := make([]string, 0, len(set))
	for city := range set {
		result = append(result, city)
	}
	sort.Strings(result)
	return result, nil
}

func round(value float64) float64 {
	return math.Round(value*1000) / 1000
}

// Ranking returns states ranked by average price for a given fuel.
// order: "desc" (most expensive first) or "asc" (cheapest first).
func (r *AnalyticsRepository) Ranking(_ context.Context, fuel, order string, limit int) ([]domain.RankingEntry, error) {
	filteredFuel := strings.ToLower(fuel)
	// Aggregate last-2-weeks history per state to compute current price and week-over-week change.
	type stateAgg struct {
		weeks  []string
		prices map[string]float64 // week -> avg price
		vol    float64
		n      int
	}
	byState := map[string]*stateAgg{}
	for _, item := range r.history {
		if filteredFuel != "" && item.Product != filteredFuel {
			continue
		}
		if item.City != "" {
			continue // only state-level rows
		}
		entry, ok := byState[item.State]
		if !ok {
			entry = &stateAgg{prices: map[string]float64{}}
			byState[item.State] = entry
		}
		// accumulate by week
		if _, seen := entry.prices[item.Week]; !seen {
			entry.weeks = append(entry.weeks, item.Week)
		}
		entry.prices[item.Week] += item.AveragePrice
		entry.vol += item.Volatility
		entry.n++
	}
	result := make([]domain.RankingEntry, 0, len(byState))
	for state, agg := range byState {
		if agg.n == 0 {
			continue
		}
		sort.Strings(agg.weeks)
		lastWeek := agg.weeks[len(agg.weeks)-1]
		currentPrice := agg.prices[lastWeek]
		changePct := 0.0
		if len(agg.weeks) >= 2 {
			prevWeek := agg.weeks[len(agg.weeks)-2]
			prevPrice := agg.prices[prevWeek]
			if prevPrice > 0 {
				changePct = round(((currentPrice / prevPrice) - 1) * 100)
			}
		}
		result = append(result, domain.RankingEntry{
			State:      state,
			Product:    filteredFuel,
			Price:      round(currentPrice),
			Volatility: round(agg.vol / float64(agg.n)),
			ChangeWeek: changePct,
		})
	}
	if order == "asc" {
		sort.Slice(result, func(i, j int) bool { return result[i].Price < result[j].Price })
	} else {
		sort.Slice(result, func(i, j int) bool { return result[i].Price > result[j].Price })
	}
	if limit > 0 && len(result) > limit {
		result = result[:limit]
	}
	for i := range result {
		result[i].Position = i + 1
	}
	return result, nil
}

// Trends returns week-over-week price changes for a given fuel/state.
func (r *AnalyticsRepository) Trends(_ context.Context, fuel, state, startDate, endDate string) ([]domain.TrendPoint, error) {
	history, err := r.History(context.Background(), fuel, state, "", startDate, endDate)
	if err != nil {
		return nil, err
	}
	result := make([]domain.TrendPoint, 0, len(history))
	for i, item := range history {
		point := domain.TrendPoint{
			Week:  item.Week,
			Price: round(item.AveragePrice),
		}
		if i > 0 {
			prev := history[i-1].AveragePrice
			point.ChangeAbs = round(item.AveragePrice - prev)
			if prev > 0 {
				point.ChangePct = round(((item.AveragePrice / prev) - 1) * 100)
			}
		}
		result = append(result, point)
	}
	return result, nil
}

// Stats returns aggregate national statistics for a given fuel.
func (r *AnalyticsRepository) Stats(_ context.Context, fuel, startDate, endDate string) (domain.NationalStats, error) {
	overview, err := r.Overview(context.Background(), fuel, "", startDate, endDate)
	if err != nil || len(overview) == 0 {
		return domain.NationalStats{Product: fuel}, err
	}
	minPrice := overview[0].AveragePrice
	maxPrice := overview[0].AveragePrice
	minState := overview[0].State
	maxState := overview[0].State
	total := 0.0
	for _, item := range overview {
		total += item.AveragePrice
		if item.AveragePrice < minPrice {
			minPrice = item.AveragePrice
			minState = item.State
		}
		if item.AveragePrice > maxPrice {
			maxPrice = item.AveragePrice
			maxState = item.State
		}
	}
	// National week-over-week: compare last 2 weeks across all states
	history, _ := r.History(context.Background(), fuel, "", "", "", "")
	type weekAgg struct {
		total float64
		n     int
	}
	weekMap := map[string]*weekAgg{}
	for _, item := range history {
		if item.City != "" {
			continue
		}
		entry, ok := weekMap[item.Week]
		if !ok {
			entry = &weekAgg{}
			weekMap[item.Week] = entry
		}
		entry.total += item.AveragePrice
		entry.n++
	}
	weeks := make([]string, 0, len(weekMap))
	for w := range weekMap {
		weeks = append(weeks, w)
	}
	sort.Strings(weeks)
	changePct := 0.0
	if len(weeks) >= 2 {
		last := weekMap[weeks[len(weeks)-1]]
		prev := weekMap[weeks[len(weeks)-2]]
		lastAvg := last.total / float64(last.n)
		prevAvg := prev.total / float64(prev.n)
		if prevAvg > 0 {
			changePct = round(((lastAvg / prevAvg) - 1) * 100)
		}
	}
	return domain.NationalStats{
		Product:       fuel,
		NationalAvg:   round(total / float64(len(overview))),
		MinPrice:      round(minPrice),
		MaxPrice:      round(maxPrice),
		MinState:      minState,
		MaxState:      maxState,
		StateCount:    len(overview),
		ChangeWeekPct: changePct,
	}, nil
}
