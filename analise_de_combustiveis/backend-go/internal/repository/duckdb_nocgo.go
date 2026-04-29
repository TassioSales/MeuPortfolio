//go:build !cgo
package repository

import (
	"context"
	"fmt"
	"fuel-analytics-api/internal/domain"
)

type DuckDBRepository struct{}

func NewDuckDBRepository(dbPath string) (*DuckDBRepository, error) {
	return nil, fmt.Errorf("duckdb repository is disabled (requires CGO and a C compiler)")
}

func (r *DuckDBRepository) Health(ctx context.Context) error {
	return fmt.Errorf("duckdb disabled")
}

func (r *DuckDBRepository) Fuels(ctx context.Context) ([]string, error) {
	return nil, fmt.Errorf("duckdb disabled")
}

func (r *DuckDBRepository) Overview(ctx context.Context, fuel, state, startDate, endDate string) ([]domain.FuelSummary, error) {
	return nil, fmt.Errorf("duckdb repository is disabled (requires CGO and a C compiler)")
}

func (r *DuckDBRepository) History(ctx context.Context, fuel, state, city, startDate, endDate string) ([]domain.HistoryPoint, error) {
	return nil, fmt.Errorf("duckdb repository is disabled (requires CGO and a C compiler)")
}

func (r *DuckDBRepository) Cities(ctx context.Context, fuel, state string) ([]string, error) {
	return nil, fmt.Errorf("duckdb repository is disabled (requires CGO and a C compiler)")
}

func (r *DuckDBRepository) Forecast(ctx context.Context, fuel, state, startDate, endDate string) ([]domain.ForecastPoint, error) {
	return nil, fmt.Errorf("duckdb repository is disabled (requires CGO and a C compiler)")
}

func (r *DuckDBRepository) Compare(ctx context.Context, fuel, compareWith, state, startDate, endDate string) ([]domain.ComparisonPoint, error) {
	return nil, fmt.Errorf("duckdb repository is disabled (requires CGO and a C compiler)")
}

func (r *DuckDBRepository) Map(ctx context.Context, fuel string) ([]domain.FuelSummary, error) {
	return nil, fmt.Errorf("duckdb repository is disabled (requires CGO and a C compiler)")
}

func (r *DuckDBRepository) Market(ctx context.Context, fuel, state, startDate, endDate string) ([]domain.MarketSignal, error) {
	return nil, fmt.Errorf("duckdb repository is disabled (requires CGO and a C compiler)")
}

func (r *DuckDBRepository) Explorer(ctx context.Context) (domain.ExplorerPayload, error) {
	return domain.ExplorerPayload{}, fmt.Errorf("duckdb disabled")
}
