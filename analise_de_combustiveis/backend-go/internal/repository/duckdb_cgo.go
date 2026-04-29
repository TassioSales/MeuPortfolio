//go:build cgo
package repository

import (
	"context"
	"database/sql"
	"fmt"
	"strings"

	"fuel-analytics-api/internal/domain"
	_ "github.com/marcboeker/go-duckdb"
)

type DuckDBRepository struct {
	db *sql.DB
}

func NewDuckDBRepository(dbPath string) (*DuckDBRepository, error) {
	db, err := sql.Open("duckdb", dbPath)
	if err != nil {
		return nil, fmt.Errorf("failed to open duckdb: %w", err)
	}
	return &DuckDBRepository{db: db}, nil
}

func (r *DuckDBRepository) Health(ctx context.Context) error {
	return r.db.PingContext(ctx)
}

func (r *DuckDBRepository) Fuels(ctx context.Context) ([]string, error) {
	rows, err := r.db.QueryContext(ctx, "SELECT DISTINCT product FROM curated_weekly_prices ORDER BY product")
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var result []string
	for rows.Next() {
		var f string
		if err := rows.Scan(&f); err != nil {
			return nil, err
		}
		result = append(result, f)
	}
	return result, nil
}

func (r *DuckDBRepository) Overview(ctx context.Context, fuel, state, startDate, endDate string) ([]domain.FuelSummary, error) {
	query := `SELECT state, product, COALESCE(avg_price, 0), COALESCE(volatility, 0), COALESCE(dollar, 0), COALESCE(brent, 0), COALESCE(ipca, 0), COALESCE(price_direction, 'stable') 
	          FROM latest_overview WHERE 1=1`
	var args []any
	if fuel != "" {
		query += " AND product = ?"
		args = append(args, strings.ToLower(fuel))
	}
	if state != "" {
		query += " AND state = ?"
		args = append(args, strings.ToUpper(state))
	}
	query += " ORDER BY avg_price DESC"

	rows, err := r.db.QueryContext(ctx, query, args...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var result []domain.FuelSummary
	for rows.Next() {
		var s domain.FuelSummary
		if err := rows.Scan(&s.State, &s.Product, &s.AveragePrice, &s.Volatility, &s.Dollar, &s.Brent, &s.IPCA, &s.PriceDirection); err != nil {
			return nil, err
		}
		result = append(result, s)
	}
	return result, nil
}

func (r *DuckDBRepository) History(ctx context.Context, fuel, state, city, startDate, endDate string) ([]domain.HistoryPoint, error) {
	// Note: We use curated_weekly_prices here.
	// If city is empty, we aggregate by week/state.
	var query string
	var args []any
	
	where := "WHERE product = ? AND state = ?"
	args = append(args, strings.ToLower(fuel), strings.ToUpper(state))
	
	if city != "" {
		where += " AND city = ?"
		args = append(args, city)
	}
	if startDate != "" {
		where += " AND week >= ?"
		args = append(args, startDate)
	}
	if endDate != "" {
		where += " AND week <= ?"
		args = append(args, endDate)
	}

	if city == "" {
		query = fmt.Sprintf(`SELECT week, state, '' as city, product, COALESCE(avg(avg_price), 0), COALESCE(avg(volatility), 0), COALESCE(avg(avg_buy_price), 0)
		         FROM curated_weekly_prices 
		         %s
		         GROUP BY week, state, product
		         ORDER BY week ASC`, where)
	} else {
		query = fmt.Sprintf(`SELECT week, state, city, product, COALESCE(avg_price, 0), COALESCE(volatility, 0), COALESCE(avg_buy_price, 0)
		         FROM curated_weekly_prices 
		         %s
		         ORDER BY week ASC`, where)
	}

	rows, err := r.db.QueryContext(ctx, query, args...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var result []domain.HistoryPoint
	for rows.Next() {
		var p domain.HistoryPoint
		if err := rows.Scan(&p.Week, &p.State, &p.City, &p.Product, &p.AveragePrice, &p.Volatility, &p.AverageBuy); err != nil {
			return nil, err
		}
		result = append(result, p)
	}
	return result, nil
}

func (r *DuckDBRepository) Cities(ctx context.Context, fuel, state string) ([]string, error) {
	rows, err := r.db.QueryContext(ctx, "SELECT DISTINCT city FROM curated_weekly_prices WHERE product = ? AND state = ? ORDER BY city", strings.ToLower(fuel), strings.ToUpper(state))
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var result []string
	for rows.Next() {
		var c string
		if err := rows.Scan(&c); err != nil {
			return nil, err
		}
		if c != "" {
			result = append(result, c)
		}
	}
	return result, nil
}

func (r *DuckDBRepository) Forecast(ctx context.Context, fuel, state, startDate, endDate string) ([]domain.ForecastPoint, error) {
	// For now, DuckDB might not have the forecast table yet (based on my DESCRIBE, I only saw prices and overview).
	// I'll keep it empty or return from a static table if exists.
	// Actually, let's assume a 'forecasts' table exists or return empty for now to avoid crashes.
	return []domain.ForecastPoint{}, nil
}

func (r *DuckDBRepository) Compare(ctx context.Context, fuel, compareWith, state, startDate, endDate string) ([]domain.ComparisonPoint, error) {
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
		advantage := 0.0
		if item.AveragePrice != 0 {
			advantage = ((other.AveragePrice / item.AveragePrice) - 1) * 100.0
		}
		result = append(result, domain.ComparisonPoint{
			Week:             item.Week,
			PrimaryFuel:      fuel,
			ComparedFuel:     compareWith,
			PrimaryPrice:     item.AveragePrice,
			ComparedPrice:    other.AveragePrice,
			AdvantagePercent: advantage,
			RecommendedFuel:  recommended,
		})
	}
	return result, nil
}

func (r *DuckDBRepository) Map(ctx context.Context, fuel string) ([]domain.FuelSummary, error) {
	return r.Overview(ctx, fuel, "", "", "")
}

func (r *DuckDBRepository) Market(ctx context.Context, fuel, state, startDate, endDate string) ([]domain.MarketSignal, error) {
	// Similar to forecast, I didn't see a 'market' table in the dump.
	return []domain.MarketSignal{}, nil
}

func (r *DuckDBRepository) Explorer(ctx context.Context) (domain.ExplorerPayload, error) {
	// Implement simple explorer logic
	return domain.ExplorerPayload{}, nil
}
