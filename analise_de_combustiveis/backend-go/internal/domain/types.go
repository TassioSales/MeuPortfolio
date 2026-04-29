package domain

import (
	"context"
	"encoding/json"
)

type FuelSummary struct {
	Product        string  `json:"product"`
	State          string  `json:"state"`
	AveragePrice   float64 `json:"average_price"`
	Volatility     float64 `json:"volatility"`
	Dollar         float64 `json:"dollar"`
	Brent          float64 `json:"brent"`
	IPCA           float64 `json:"ipca"`
	PriceDirection string  `json:"price_direction"`
}

func (f *FuelSummary) UnmarshalJSON(data []byte) error {
	type fuelSummaryAlias struct {
		Product        string   `json:"product"`
		State          string   `json:"state"`
		AveragePrice   *float64 `json:"average_price"`
		LegacyAvgPrice *float64 `json:"avg_price"`
		Volatility     float64  `json:"volatility"`
		Dollar         float64  `json:"dollar"`
		Brent          float64  `json:"brent"`
		IPCA           float64  `json:"ipca"`
		PriceDirection string   `json:"price_direction"`
	}

	var payload fuelSummaryAlias
	if err := json.Unmarshal(data, &payload); err != nil {
		return err
	}

	f.Product = payload.Product
	f.State = payload.State
	f.Volatility = payload.Volatility
	f.Dollar = payload.Dollar
	f.Brent = payload.Brent
	f.IPCA = payload.IPCA
	f.PriceDirection = payload.PriceDirection
	if payload.AveragePrice != nil {
		f.AveragePrice = *payload.AveragePrice
	} else if payload.LegacyAvgPrice != nil {
		f.AveragePrice = *payload.LegacyAvgPrice
	}
	return nil
}

type HistoryPoint struct {
	Week         string  `json:"week"`
	State        string  `json:"state"`
	City         string  `json:"city"`
	Product      string  `json:"product"`
	AveragePrice float64 `json:"average_price"`
	Volatility   float64 `json:"volatility"`
	AverageBuy   float64 `json:"average_buy_price"`
}

type ComparisonPoint struct {
	Week             string  `json:"week"`
	PrimaryFuel      string  `json:"primary_fuel"`
	ComparedFuel     string  `json:"compared_fuel"`
	PrimaryPrice     float64 `json:"primary_price"`
	ComparedPrice    float64 `json:"compared_price"`
	AdvantagePercent float64 `json:"advantage_percent"`
	RecommendedFuel  string  `json:"recommended_fuel"`
}

type ForecastPoint struct {
	Week      string  `json:"week"`
	Predicted float64 `json:"predicted"`
	Minimum   float64 `json:"minimum"`
	Maximum   float64 `json:"maximum"`
	Scenario  string  `json:"scenario"`
}

type InsightPayload struct {
	Title   string   `json:"title"`
	Summary string   `json:"summary"`
	Bullets []string `json:"bullets"`
	Source  string   `json:"source"`
}

type MarketSignal struct {
	Month             string  `json:"month"`
	State             string  `json:"state"`
	Product           string  `json:"product"`
	SalesVolumeM3     float64 `json:"sales_volume_m3"`
	ProcessedM3       float64 `json:"processed_m3"`
	ProducedM3        float64 `json:"produced_m3"`
	SupplyDemandRatio float64 `json:"supply_demand_ratio"`
	RefineryGapM3     float64 `json:"refinery_gap_m3"`
	MarketRegime      string  `json:"market_regime"`
}

type ExplorerTable struct {
	Table      string                   `json:"table"`
	RowCount   int64                    `json:"row_count"`
	SampleRows []map[string]interface{} `json:"sample_rows"`
}

type ExplorerPayload struct {
	WarehousePath string          `json:"warehouse_path"`
	Tables        []ExplorerTable `json:"tables"`
}

type Repository interface {
	Health(ctx context.Context) error
	Fuels(ctx context.Context) ([]string, error)
	Overview(ctx context.Context, fuel, state, startDate, endDate string) ([]FuelSummary, error)
	History(ctx context.Context, fuel, state, city, startDate, endDate string) ([]HistoryPoint, error)
	Cities(ctx context.Context, fuel, state string) ([]string, error)
	Forecast(ctx context.Context, fuel, state, startDate, endDate string) ([]ForecastPoint, error)
	Compare(ctx context.Context, fuel, compareWith, state, startDate, endDate string) ([]ComparisonPoint, error)
	Map(ctx context.Context, fuel string) ([]FuelSummary, error)
	Market(ctx context.Context, fuel, state, startDate, endDate string) ([]MarketSignal, error)
	Explorer(ctx context.Context) (ExplorerPayload, error)
}
