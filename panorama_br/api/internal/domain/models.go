package domain

// MacroIndicator — snapshot de um indicador macro
type MacroIndicator struct {
	Indicator string  `json:"indicator"`
	Value     float64 `json:"value"`
	Unit      string  `json:"unit"`
	RefDate   string  `json:"ref_date"`
	UpdatedAt string  `json:"updated_at"`
}

// MacroResponse — resposta de /api/v1/macro
type MacroResponse struct {
	Indicators  map[string]MacroIndicator `json:"indicators"`
	LastUpdated string                    `json:"last_updated"`
}

// HistoryPoint — ponto de série temporal
type HistoryPoint struct {
	Date  string  `json:"date"`
	Value float64 `json:"value"`
}

// StockItem — ativo do mercado
type StockItem struct {
	Symbol    string  `json:"symbol"`
	Name      string  `json:"name"`
	Price     float64 `json:"price"`
	ChangePct float64 `json:"change_pct"`
	Volume    float64 `json:"volume"`
	MarketCap float64 `json:"market_cap"`
	UpdatedAt string  `json:"updated_at"`
}

// MarketResponse — resposta de /api/v1/market
type MarketResponse struct {
	Ibovespa    *StockItem  `json:"ibovespa"`
	Stocks      []StockItem `json:"stocks"`
	LastUpdated string      `json:"last_updated"`
}

// RegionalData — dados por estado
type RegionalData struct {
	UF           string  `json:"uf"`
	Year         int     `json:"year"`
	StateName    string  `json:"state_name"`
	Region       string  `json:"region"`
	PIB          float64 `json:"pib"`
	PIBPerCapita float64 `json:"pib_per_capita"`
	Population   int64   `json:"population"`
	Desemprego   float64 `json:"desemprego"`
}

// StatusResponse — health check
type StatusResponse struct {
	Status          string `json:"status"`
	PipelineLastRun string `json:"pipeline_last_run"`
	RecordsCount    int    `json:"records_count"`
	DBPath          string `json:"db_path"`
}
