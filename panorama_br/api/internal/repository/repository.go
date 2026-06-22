package repository

import (
	"database/sql"
	"fmt"

	"github.com/tassiosales/panorama_br/internal/domain"
	_ "modernc.org/sqlite"
)

type Repository struct {
	db *sql.DB
}

func New(dbPath string) (*Repository, error) {
	db, err := sql.Open("sqlite", dbPath+"?_journal=WAL&_timeout=5000")
	if err != nil {
		return nil, err
	}
	if err := db.Ping(); err != nil {
		return nil, err
	}
	return &Repository{db: db}, nil
}

func (r *Repository) Close() {
	r.db.Close()
}

// GetMacroIndicators retorna todos os indicadores macro
func (r *Repository) GetMacroIndicators() (map[string]domain.MacroIndicator, error) {
	rows, err := r.db.Query(`SELECT indicator, value, unit, ref_date, updated_at FROM macro_indicators`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	result := make(map[string]domain.MacroIndicator)
	for rows.Next() {
		var m domain.MacroIndicator
		if err := rows.Scan(&m.Indicator, &m.Value, &m.Unit, &m.RefDate, &m.UpdatedAt); err != nil {
			return nil, err
		}
		result[m.Indicator] = m
	}
	return result, rows.Err()
}

// GetIndicatorHistory retorna pontos históricos de um indicador nos últimos N dias
func (r *Repository) GetIndicatorHistory(indicator string, days int) ([]domain.HistoryPoint, error) {
	cutoff := fmt.Sprintf("date('now', '-%d days')", days)
	query := fmt.Sprintf(
		`SELECT date, value FROM indicator_history WHERE indicator=? AND date >= %s ORDER BY date ASC`,
		cutoff,
	)
	rows, err := r.db.Query(query, indicator)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var points []domain.HistoryPoint
	for rows.Next() {
		var p domain.HistoryPoint
		if err := rows.Scan(&p.Date, &p.Value); err != nil {
			return nil, err
		}
		points = append(points, p)
	}
	return points, rows.Err()
}

// GetMarketSnapshot retorna todos os ativos ordenados por market_cap
func (r *Repository) GetMarketSnapshot() ([]domain.StockItem, error) {
	rows, err := r.db.Query(`SELECT symbol, name, price, change_pct, volume, market_cap, updated_at FROM market_snapshot ORDER BY market_cap DESC`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var items []domain.StockItem
	for rows.Next() {
		var s domain.StockItem
		if err := rows.Scan(&s.Symbol, &s.Name, &s.Price, &s.ChangePct, &s.Volume, &s.MarketCap, &s.UpdatedAt); err != nil {
			return nil, err
		}
		items = append(items, s)
	}
	return items, rows.Err()
}

// GetRegionalData retorna dados regionais ordenados por PIB
func (r *Repository) GetRegionalData() ([]domain.RegionalData, error) {
	rows, err := r.db.Query(`SELECT uf, year, state_name, region, pib, pib_per_capita, population, desemprego FROM regional_indicators ORDER BY pib DESC`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var data []domain.RegionalData
	for rows.Next() {
		var d domain.RegionalData
		if err := rows.Scan(&d.UF, &d.Year, &d.StateName, &d.Region, &d.PIB, &d.PIBPerCapita, &d.Population, &d.Desemprego); err != nil {
			return nil, err
		}
		data = append(data, d)
	}
	return data, rows.Err()
}

// GetLastPipelineRun retorna o timestamp da última execução do pipeline
func (r *Repository) GetLastPipelineRun() (string, error) {
	var runAt string
	err := r.db.QueryRow(`SELECT run_at FROM pipeline_log ORDER BY id DESC LIMIT 1`).Scan(&runAt)
	if err != nil {
		return "", err
	}
	return runAt, nil
}

// GetRecordsCount retorna a soma de registros nas tabelas principais
func (r *Repository) GetRecordsCount() (int, error) {
	var count int
	err := r.db.QueryRow(`
		SELECT
			(SELECT COUNT(*) FROM macro_indicators) +
			(SELECT COUNT(*) FROM indicator_history) +
			(SELECT COUNT(*) FROM market_snapshot) +
			(SELECT COUNT(*) FROM regional_indicators)
	`).Scan(&count)
	if err != nil {
		return 0, err
	}
	return count, nil
}
