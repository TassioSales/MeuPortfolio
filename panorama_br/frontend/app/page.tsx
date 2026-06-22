'use client'
import { useState, useEffect, useCallback } from 'react'
import { api } from '@/lib/api'
import type {
  MacroResponse,
  MarketResponse,
  RegionalData,
  HistoryPoint,
  StatusResponse,
} from '@/lib/types'
import { fmt, changeColor, changeSign, fmtBig } from '@/lib/utils'
import MetricCard from '@/components/MetricCard'
import LineChart from '@/components/LineChart'
import BarChartComp from '@/components/BarChartComp'
import StocksTable from '@/components/StocksTable'
import RegionalMap from '@/components/RegionalMap'
import {
  ComposedChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'

// ──────────────────────────────────────────
// Mock data (fallback when API is offline)
// ──────────────────────────────────────────

function makeHistory(
  base: number,
  volatility: number,
  months = 12,
): HistoryPoint[] {
  const now = new Date()
  return Array.from({ length: months }, (_, i) => {
    const d = new Date(now.getFullYear(), now.getMonth() - (months - 1 - i), 1)
    const date = d.toISOString().slice(0, 10)
    const rand = (Math.random() - 0.5) * 2 * volatility
    return { date, value: parseFloat((base + rand).toFixed(2)) }
  })
}

const MOCK_MACRO: MacroResponse = {
  indicators: {
    selic_atual: { value: 10.5, unit: '% a.a.', ref_date: '2024-01', updated_at: new Date().toISOString() },
    ipca_mensal: { value: 0.44, unit: '%', ref_date: '2024-01', updated_at: new Date().toISOString() },
    ipca_12m: { value: 4.83, unit: '%', ref_date: '2024-01', updated_at: new Date().toISOString() },
    cambio_usd: { value: 4.97, unit: 'R$/USD', ref_date: '2024-01', updated_at: new Date().toISOString() },
    desemprego: { value: 7.8, unit: '%', ref_date: '2023-Q3', updated_at: new Date().toISOString() },
  },
  last_updated: new Date().toISOString(),
}

const MOCK_HISTORY: Record<string, HistoryPoint[]> = {
  selic_atual: makeHistory(10.5, 0.5),
  ipca_mensal: makeHistory(0.44, 0.15),
  ipca_12m: makeHistory(4.83, 0.3),
  cambio_usd: makeHistory(4.97, 0.25),
  desemprego: makeHistory(7.8, 0.4),
}

const MOCK_MARKET: MarketResponse = {
  ibovespa: {
    symbol: '^BVSP',
    name: 'Ibovespa',
    price: 128450.0,
    change_pct: 0.87,
    volume: 12500000000,
    market_cap: 0,
    updated_at: new Date().toISOString(),
  },
  stocks: [
    { symbol: 'PETR4.SA', name: 'Petrobras PN', price: 38.42, change_pct: 1.23, volume: 85000000, market_cap: 497000000000, updated_at: new Date().toISOString() },
    { symbol: 'VALE3.SA', name: 'Vale ON', price: 65.18, change_pct: -0.54, volume: 62000000, market_cap: 287000000000, updated_at: new Date().toISOString() },
    { symbol: 'ITUB4.SA', name: 'Itaú Unibanco PN', price: 32.75, change_pct: 0.46, volume: 48000000, market_cap: 319000000000, updated_at: new Date().toISOString() },
    { symbol: 'BBDC4.SA', name: 'Bradesco PN', price: 14.22, change_pct: -1.11, volume: 55000000, market_cap: 148000000000, updated_at: new Date().toISOString() },
    { symbol: 'ABEV3.SA', name: 'Ambev ON', price: 11.85, change_pct: 0.25, volume: 32000000, market_cap: 186000000000, updated_at: new Date().toISOString() },
    { symbol: 'MGLU3.SA', name: 'Magazine Luiza ON', price: 2.44, change_pct: -2.8, volume: 95000000, market_cap: 15000000000, updated_at: new Date().toISOString() },
    { symbol: 'WEGE3.SA', name: 'WEG ON', price: 48.9, change_pct: 1.67, volume: 18000000, market_cap: 236000000000, updated_at: new Date().toISOString() },
  ],
  last_updated: new Date().toISOString(),
}

const MOCK_REGIONAL: RegionalData[] = [
  { uf: 'SP', year: 2022, state_name: 'São Paulo', region: 'Sudeste', pib: 2800, pib_per_capita: 60500, population: 46300000, desemprego: 6.8 },
  { uf: 'RJ', year: 2022, state_name: 'Rio de Janeiro', region: 'Sudeste', pib: 850, pib_per_capita: 48200, population: 17600000, desemprego: 11.2 },
  { uf: 'MG', year: 2022, state_name: 'Minas Gerais', region: 'Sudeste', pib: 700, pib_per_capita: 32800, population: 21300000, desemprego: 7.4 },
  { uf: 'RS', year: 2022, state_name: 'Rio Grande do Sul', region: 'Sul', pib: 520, pib_per_capita: 45600, population: 11400000, desemprego: 5.9 },
  { uf: 'PR', year: 2022, state_name: 'Paraná', region: 'Sul', pib: 480, pib_per_capita: 41800, population: 11500000, desemprego: 5.4 },
  { uf: 'SC', year: 2022, state_name: 'Santa Catarina', region: 'Sul', pib: 340, pib_per_capita: 46200, population: 7300000, desemprego: 3.8 },
  { uf: 'BA', year: 2022, state_name: 'Bahia', region: 'Nordeste', pib: 290, pib_per_capita: 18900, population: 15400000, desemprego: 14.2 },
  { uf: 'GO', year: 2022, state_name: 'Goiás', region: 'Centro-Oeste', pib: 260, pib_per_capita: 36800, population: 7100000, desemprego: 6.2 },
  { uf: 'MT', year: 2022, state_name: 'Mato Grosso', region: 'Centro-Oeste', pib: 210, pib_per_capita: 57900, population: 3600000, desemprego: 4.7 },
  { uf: 'PE', year: 2022, state_name: 'Pernambuco', region: 'Nordeste', pib: 200, pib_per_capita: 20200, population: 9900000, desemprego: 13.8 },
  { uf: 'CE', year: 2022, state_name: 'Ceará', region: 'Nordeste', pib: 175, pib_per_capita: 18800, population: 9300000, desemprego: 12.4 },
  { uf: 'AM', year: 2022, state_name: 'Amazonas', region: 'Norte', pib: 165, pib_per_capita: 37200, population: 4400000, desemprego: 9.1 },
  { uf: 'PA', year: 2022, state_name: 'Pará', region: 'Norte', pib: 155, pib_per_capita: 17200, population: 9000000, desemprego: 9.8 },
  { uf: 'DF', year: 2022, state_name: 'Distrito Federal', region: 'Centro-Oeste', pib: 280, pib_per_capita: 88400, population: 3200000, desemprego: 7.6 },
  { uf: 'ES', year: 2022, state_name: 'Espírito Santo', region: 'Sudeste', pib: 150, pib_per_capita: 36800, population: 4100000, desemprego: 6.5 },
  { uf: 'MS', year: 2022, state_name: 'Mato Grosso do Sul', region: 'Centro-Oeste', pib: 130, pib_per_capita: 45200, population: 2900000, desemprego: 4.9 },
  { uf: 'MA', year: 2022, state_name: 'Maranhão', region: 'Nordeste', pib: 105, pib_per_capita: 14800, population: 7100000, desemprego: 13.1 },
  { uf: 'RN', year: 2022, state_name: 'Rio Grande do Norte', region: 'Nordeste', pib: 80, pib_per_capita: 21900, population: 3600000, desemprego: 12.6 },
  { uf: 'PI', year: 2022, state_name: 'Piauí', region: 'Nordeste', pib: 60, pib_per_capita: 17200, population: 3500000, desemprego: 11.8 },
  { uf: 'AL', year: 2022, state_name: 'Alagoas', region: 'Nordeste', pib: 55, pib_per_capita: 15600, population: 3500000, desemprego: 15.4 },
  { uf: 'PB', year: 2022, state_name: 'Paraíba', region: 'Nordeste', pib: 70, pib_per_capita: 16200, population: 4300000, desemprego: 11.2 },
  { uf: 'SE', year: 2022, state_name: 'Sergipe', region: 'Nordeste', pib: 45, pib_per_capita: 18900, population: 2400000, desemprego: 13.5 },
  { uf: 'RO', year: 2022, state_name: 'Rondônia', region: 'Norte', pib: 50, pib_per_capita: 27600, population: 1800000, desemprego: 6.8 },
  { uf: 'TO', year: 2022, state_name: 'Tocantins', region: 'Norte', pib: 42, pib_per_capita: 25800, population: 1600000, desemprego: 7.2 },
  { uf: 'AC', year: 2022, state_name: 'Acre', region: 'Norte', pib: 18, pib_per_capita: 18900, population: 950000, desemprego: 8.5 },
  { uf: 'AP', year: 2022, state_name: 'Amapá', region: 'Norte', pib: 16, pib_per_capita: 18200, population: 880000, desemprego: 10.2 },
  { uf: 'RR', year: 2022, state_name: 'Roraima', region: 'Norte', pib: 14, pib_per_capita: 19800, population: 710000, desemprego: 9.4 },
]

const INDICATOR_LABELS: Record<string, string> = {
  selic_atual: 'SELIC',
  ipca_mensal: 'IPCA Mensal',
  ipca_12m: 'IPCA 12m',
  cambio_usd: 'USD/BRL',
  desemprego: 'Desemprego',
}

const TABS = [
  { id: 'macro', label: '📈 Macro', desc: 'Indicadores Macroeconômicos' },
  { id: 'mercado', label: '💹 Mercado', desc: 'Bolsa e Ações' },
  { id: 'regional', label: '🗺️ Regional', desc: 'Dados por Estado' },
  { id: 'comparativo', label: '📊 Comparativo', desc: 'Compare Indicadores' },
] as const

type TabId = (typeof TABS)[number]['id']

// ──────────────────────────────────────────
// Main Page Component
// ──────────────────────────────────────────

export default function DashboardPage() {
  const [activeTab, setActiveTab] = useState<TabId>('macro')
  const [macro, setMacro] = useState<MacroResponse | null>(null)
  const [market, setMarket] = useState<MarketResponse | null>(null)
  const [regional, setRegional] = useState<RegionalData[]>([])
  const [status, setStatus] = useState<StatusResponse | null>(null)
  const [history, setHistory] = useState<Record<string, HistoryPoint[]>>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [regionMetric, setRegionMetric] = useState<'pib_per_capita' | 'desemprego' | 'pib'>(
    'pib_per_capita',
  )
  const [compareA, setCompareA] = useState('selic_atual')
  const [compareB, setCompareB] = useState('ipca_12m')
  const [historyB, setHistoryB] = useState<HistoryPoint[]>([])

  const loadData = useCallback(async () => {
    try {
      const [macroRes, marketRes, regionalRes, statusRes] = await Promise.allSettled([
        api.macro(),
        api.market(),
        api.regional(),
        api.status(),
      ])

      const indicators = ['selic_atual', 'ipca_mensal', 'ipca_12m', 'cambio_usd', 'desemprego']
      const historyResults = await Promise.allSettled(
        indicators.map((ind) => api.history(ind, 90)),
      )

      if (macroRes.status === 'fulfilled') {
        setMacro(macroRes.value)
      } else {
        setMacro(MOCK_MACRO)
        setError('API offline — exibindo dados de demonstração')
      }

      if (marketRes.status === 'fulfilled') {
        setMarket(marketRes.value)
      } else {
        setMarket(MOCK_MARKET)
      }

      if (regionalRes.status === 'fulfilled') {
        setRegional(regionalRes.value)
      } else {
        setRegional(MOCK_REGIONAL)
      }

      if (statusRes.status === 'fulfilled') {
        setStatus(statusRes.value)
      }

      const histMap: Record<string, HistoryPoint[]> = {}
      indicators.forEach((ind, i) => {
        const r = historyResults[i]
        histMap[ind] = r.status === 'fulfilled' ? r.value : MOCK_HISTORY[ind]
      })
      setHistory(histMap)
    } catch {
      setMacro(MOCK_MACRO)
      setMarket(MOCK_MARKET)
      setRegional(MOCK_REGIONAL)
      setHistory(MOCK_HISTORY)
      setError('API offline — exibindo dados de demonstração')
    } finally {
      setLoading(false)
    }
  }, [])

  // Load historyB whenever compareB changes
  useEffect(() => {
    if (!history[compareB]) return
    setHistoryB(history[compareB])
  }, [compareB, history])

  useEffect(() => {
    loadData()
    const interval = setInterval(loadData, 5 * 60 * 1000)
    return () => clearInterval(interval)
  }, [loadData])

  // ── Loading ──
  if (loading) {
    return (
      <div className="min-h-screen bg-bg flex items-center justify-center">
        <div className="text-center">
          <div className="text-4xl mb-4 animate-spin">🇧🇷</div>
          <p className="text-muted">Carregando indicadores...</p>
        </div>
      </div>
    )
  }

  const macroData = macro ?? MOCK_MACRO
  const marketData = market ?? MOCK_MARKET
  const regionalData = regional.length ? regional : MOCK_REGIONAL

  // ── Helpers ──
  const ind = macroData.indicators

  const selicVal = ind.selic_atual?.value ?? 0
  const ipcaMes = ind.ipca_mensal?.value ?? 0
  const ipca12 = ind.ipca_12m?.value ?? 0
  const cambio = ind.cambio_usd?.value ?? 0
  const desemprego = ind.desemprego?.value ?? 0

  // Computed compare chart data (merge two histories by date)
  const histA = history[compareA] ?? MOCK_HISTORY[compareA] ?? []
  const histBData = historyB.length ? historyB : MOCK_HISTORY[compareB] ?? []
  const compareChartData = histA.map((pt) => {
    const bPt = histBData.find((b) => b.date === pt.date)
    return { date: pt.date.slice(5), a: pt.value, b: bPt?.value ?? null }
  })

  // Stats helpers
  function stats(pts: HistoryPoint[]) {
    if (!pts.length) return { min: 0, max: 0, avg: 0, change: 0 }
    const vals = pts.map((p) => p.value)
    const min = Math.min(...vals)
    const max = Math.max(...vals)
    const avg = vals.reduce((a, b) => a + b, 0) / vals.length
    const change = vals.length > 1 ? vals[vals.length - 1] - vals[0] : 0
    return { min, max, avg, change }
  }

  const statsA = stats(histA)
  const statsB = stats(histBData)

  // Top-10 regional by metric
  const top10 = [...regionalData]
    .sort((a, b) =>
      regionMetric === 'desemprego'
        ? b[regionMetric] - a[regionMetric]
        : b[regionMetric] - a[regionMetric],
    )
    .slice(0, 10)
    .map((d) => ({ name: d.uf, value: d[regionMetric] as number }))

  return (
    <div className="min-h-screen bg-bg">
      {/* ── Header ── */}
      <header className="border-b border-border bg-panel sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-text flex items-center gap-2">
              🇧🇷 <span>Panorama BR</span>
            </h1>
            <p className="text-muted text-xs">Indicadores Econômicos do Brasil</p>
          </div>
          <div className="flex items-center gap-4">
            {status && (
              <div className="text-xs text-muted text-right">
                <span className={status.status === 'ok' ? 'text-positive' : 'text-negative'}>
                  ⬤
                </span>{' '}
                Atualizado:{' '}
                {new Date(status.pipeline_last_run || Date.now()).toLocaleString('pt-BR')}
              </div>
            )}
          </div>
        </div>
      </header>

      {/* ── Error banner ── */}
      {error && (
        <div className="bg-yellow-900/30 border-b border-yellow-700/50 text-yellow-400 text-xs px-4 py-2 text-center">
          ⚠ {error}
        </div>
      )}

      {/* ── Tabs ── */}
      <div className="border-b border-border bg-panel">
        <div className="max-w-7xl mx-auto px-4">
          <div className="flex gap-0 overflow-x-auto">
            {TABS.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-5 py-4 text-sm font-medium whitespace-nowrap transition-colors border-b-2 ${
                  activeTab === tab.id
                    ? 'border-accent text-accent'
                    : 'border-transparent text-muted hover:text-text'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* ── Content ── */}
      <main className="max-w-7xl mx-auto px-4 py-6">
        {/* ──────────────── MACRO TAB ──────────────── */}
        {activeTab === 'macro' && (
          <div className="space-y-8">
            {/* KPI Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              <MetricCard
                label="SELIC"
                value={fmt(selicVal)}
                unit="% a.a."
                sub={`Meta do Banco Central`}
                trend="neutral"
              />
              <MetricCard
                label="IPCA Mensal"
                value={fmt(ipcaMes)}
                unit="%"
                sub={`Inflação do mês`}
                trend={ipcaMes > 0.5 ? 'up' : 'down'}
              />
              <MetricCard
                label="IPCA 12 meses"
                value={fmt(ipca12)}
                unit="%"
                sub={`Acumulado anual`}
                trend={ipca12 > 4.5 ? 'up' : 'neutral'}
              />
              <MetricCard
                label="Câmbio USD/BRL"
                value={fmt(cambio)}
                unit="R$/USD"
                sub={`Dólar comercial`}
                trend="neutral"
              />
              <MetricCard
                label="Desemprego"
                value={fmt(desemprego)}
                unit="%"
                sub={`Taxa PNAD`}
                trend={desemprego > 9 ? 'up' : 'down'}
              />
              <MetricCard
                label="Última Atualização"
                value={new Date(macroData.last_updated).toLocaleDateString('pt-BR')}
                sub={new Date(macroData.last_updated).toLocaleTimeString('pt-BR')}
                trend="neutral"
              />
            </div>

            {/* Charts */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              <div className="bg-panel border border-border rounded-xl p-5">
                <h3 className="text-sm font-semibold text-text mb-1">SELIC</h3>
                <p className="text-xs text-muted mb-4">Taxa básica de juros — últimos 90 dias</p>
                <LineChart
                  data={history.selic_atual ?? MOCK_HISTORY.selic_atual}
                  color="#3b82f6"
                  label="SELIC %"
                />
              </div>
              <div className="bg-panel border border-border rounded-xl p-5">
                <h3 className="text-sm font-semibold text-text mb-1">IPCA 12 meses</h3>
                <p className="text-xs text-muted mb-4">Inflação acumulada — últimos 90 dias</p>
                <LineChart
                  data={history.ipca_12m ?? MOCK_HISTORY.ipca_12m}
                  color="#f97316"
                  label="IPCA 12m %"
                />
              </div>
              <div className="bg-panel border border-border rounded-xl p-5">
                <h3 className="text-sm font-semibold text-text mb-1">Câmbio USD/BRL</h3>
                <p className="text-xs text-muted mb-4">Cotação do dólar — últimos 90 dias</p>
                <LineChart
                  data={history.cambio_usd ?? MOCK_HISTORY.cambio_usd}
                  color="#a855f7"
                  label="R$/USD"
                />
              </div>
            </div>

            {/* Desemprego chart */}
            <div className="bg-panel border border-border rounded-xl p-5">
              <h3 className="text-sm font-semibold text-text mb-1">Taxa de Desemprego</h3>
              <p className="text-xs text-muted mb-4">PNAD — últimos 90 dias</p>
              <LineChart
                data={history.desemprego ?? MOCK_HISTORY.desemprego}
                color="#10b981"
                label="Desemprego %"
              />
            </div>
          </div>
        )}

        {/* ──────────────── MERCADO TAB ──────────────── */}
        {activeTab === 'mercado' && (
          <div className="space-y-6">
            {/* IBOVESPA Hero */}
            {marketData.ibovespa && (
              <div className="bg-panel border border-border rounded-xl p-6">
                <div className="flex items-start justify-between flex-wrap gap-4">
                  <div>
                    <p className="text-muted text-sm">IBOVESPA</p>
                    <p className="text-4xl font-bold text-text mt-1">
                      {fmt(marketData.ibovespa.price, 0)}
                    </p>
                    <p className="text-muted text-xs mt-1">pontos</p>
                  </div>
                  <div className="text-right">
                    <p
                      className={`text-2xl font-bold ${changeColor(marketData.ibovespa.change_pct)}`}
                    >
                      {changeSign(marketData.ibovespa.change_pct)}
                    </p>
                    <p className="text-muted text-xs mt-1">variação do dia</p>
                    <p className="text-muted text-xs mt-2">
                      Vol: {fmtBig(marketData.ibovespa.volume)}
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Stocks Table */}
            <div className="bg-panel border border-border rounded-xl p-5">
              <h3 className="text-sm font-semibold text-text mb-4">Ações em Destaque</h3>
              <StocksTable stocks={marketData.stocks} />
            </div>

            {/* Bar chart of daily changes */}
            <div className="bg-panel border border-border rounded-xl p-5">
              <h3 className="text-sm font-semibold text-text mb-1">Variação Diária (%)</h3>
              <p className="text-xs text-muted mb-4">Performance das ações no dia</p>
              <BarChartComp
                data={marketData.stocks.map((s) => ({
                  name: s.symbol.replace('.SA', ''),
                  value: parseFloat(s.change_pct.toFixed(2)),
                }))}
                color="#3b82f6"
                label="Variação %"
              />
            </div>
          </div>
        )}

        {/* ──────────────── REGIONAL TAB ──────────────── */}
        {activeTab === 'regional' && (
          <div className="space-y-6">
            {/* Metric selector */}
            <div className="flex items-center gap-3 flex-wrap">
              <span className="text-muted text-sm">Métrica:</span>
              {(
                [
                  { key: 'pib_per_capita', label: 'PIB per capita' },
                  { key: 'desemprego', label: 'Desemprego' },
                  { key: 'pib', label: 'PIB Total' },
                ] as const
              ).map((opt) => (
                <button
                  key={opt.key}
                  onClick={() => setRegionMetric(opt.key)}
                  className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                    regionMetric === opt.key
                      ? 'bg-accent text-white'
                      : 'bg-panel border border-border text-muted hover:text-text'
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>

            {/* Map + Bar chart */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div className="bg-panel border border-border rounded-xl p-5">
                <h3 className="text-sm font-semibold text-text mb-4">
                  {regionMetric === 'pib_per_capita'
                    ? 'PIB per Capita por Estado'
                    : regionMetric === 'desemprego'
                      ? 'Taxa de Desemprego por Estado'
                      : 'PIB Total por Estado'}
                </h3>
                <RegionalMap data={regionalData} metric={regionMetric} />
              </div>

              <div className="bg-panel border border-border rounded-xl p-5">
                <h3 className="text-sm font-semibold text-text mb-4">Top 10 Estados</h3>
                <BarChartComp
                  data={top10}
                  color={regionMetric === 'desemprego' ? '#ef4444' : '#10b981'}
                  label={
                    regionMetric === 'pib_per_capita'
                      ? 'PIB per capita (R$)'
                      : regionMetric === 'desemprego'
                        ? 'Desemprego (%)'
                        : 'PIB (bi R$)'
                  }
                  horizontal
                />
              </div>
            </div>

            {/* Summary Table */}
            <div className="bg-panel border border-border rounded-xl p-5">
              <h3 className="text-sm font-semibold text-text mb-4">Resumo por Estado</h3>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-muted border-b border-border">
                      <th className="text-left py-3 px-2">UF</th>
                      <th className="text-left py-3 px-2 hidden sm:table-cell">Estado</th>
                      <th className="text-right py-3 px-2">PIB per capita</th>
                      <th className="text-right py-3 px-2">Desemprego</th>
                      <th className="text-right py-3 px-2 hidden md:table-cell">População</th>
                    </tr>
                  </thead>
                  <tbody>
                    {[...regionalData]
                      .sort((a, b) => b.pib_per_capita - a.pib_per_capita)
                      .map((d) => (
                        <tr
                          key={d.uf}
                          className="border-b border-border hover:bg-border/30 transition-colors"
                        >
                          <td className="py-3 px-2 font-semibold text-accent">{d.uf}</td>
                          <td className="py-3 px-2 text-muted hidden sm:table-cell">
                            {d.state_name}
                          </td>
                          <td className="py-3 px-2 text-right font-mono">
                            R$ {fmt(d.pib_per_capita, 0)}
                          </td>
                          <td
                            className={`py-3 px-2 text-right font-mono ${d.desemprego > 10 ? 'text-negative' : d.desemprego < 6 ? 'text-positive' : 'text-text'}`}
                          >
                            {fmt(d.desemprego)}%
                          </td>
                          <td className="py-3 px-2 text-right text-muted hidden md:table-cell">
                            {fmt(d.population / 1e6, 1)}M
                          </td>
                        </tr>
                      ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* ──────────────── COMPARATIVO TAB ──────────────── */}
        {activeTab === 'comparativo' && (
          <div className="space-y-6">
            {/* Indicator selectors */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="bg-panel border border-border rounded-xl p-4">
                <label className="text-muted text-xs block mb-2">Indicador A (azul)</label>
                <select
                  value={compareA}
                  onChange={(e) => setCompareA(e.target.value)}
                  className="w-full bg-bg border border-border rounded-lg px-3 py-2 text-text text-sm focus:outline-none focus:border-accent"
                >
                  {Object.entries(INDICATOR_LABELS).map(([key, label]) => (
                    <option key={key} value={key}>
                      {label}
                    </option>
                  ))}
                </select>
              </div>
              <div className="bg-panel border border-border rounded-xl p-4">
                <label className="text-muted text-xs block mb-2">Indicador B (laranja)</label>
                <select
                  value={compareB}
                  onChange={(e) => setCompareB(e.target.value)}
                  className="w-full bg-bg border border-border rounded-lg px-3 py-2 text-text text-sm focus:outline-none focus:border-accent"
                >
                  {Object.entries(INDICATOR_LABELS).map(([key, label]) => (
                    <option key={key} value={key}>
                      {label}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Dual-axis chart */}
            <div className="bg-panel border border-border rounded-xl p-5">
              <h3 className="text-sm font-semibold text-text mb-1">
                {INDICATOR_LABELS[compareA]} vs {INDICATOR_LABELS[compareB]}
              </h3>
              <p className="text-xs text-muted mb-4">Comparativo — últimos 90 dias</p>
              <ResponsiveContainer width="100%" height={300}>
                <ComposedChart
                  data={compareChartData}
                  margin={{ top: 5, right: 30, left: 0, bottom: 5 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                  <XAxis
                    dataKey="date"
                    tick={{ fill: '#6b7280', fontSize: 11 }}
                    tickLine={false}
                  />
                  <YAxis
                    yAxisId="left"
                    tick={{ fill: '#3b82f6', fontSize: 11 }}
                    tickLine={false}
                    width={50}
                  />
                  <YAxis
                    yAxisId="right"
                    orientation="right"
                    tick={{ fill: '#f97316', fontSize: 11 }}
                    tickLine={false}
                    width={50}
                  />
                  <Tooltip
                    contentStyle={{
                      background: '#111827',
                      border: '1px solid #1f2937',
                      borderRadius: 8,
                    }}
                    labelStyle={{ color: '#9ca3af' }}
                  />
                  <Legend
                    wrapperStyle={{ color: '#9ca3af', fontSize: 12 }}
                  />
                  <Line
                    yAxisId="left"
                    type="monotone"
                    dataKey="a"
                    stroke="#3b82f6"
                    strokeWidth={2}
                    dot={false}
                    name={INDICATOR_LABELS[compareA]}
                  />
                  <Line
                    yAxisId="right"
                    type="monotone"
                    dataKey="b"
                    stroke="#f97316"
                    strokeWidth={2}
                    dot={false}
                    name={INDICATOR_LABELS[compareB]}
                  />
                </ComposedChart>
              </ResponsiveContainer>
            </div>

            {/* Stats cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Stats A */}
              <div className="bg-panel border border-border rounded-xl p-5">
                <h3 className="text-sm font-semibold text-accent mb-4">
                  {INDICATOR_LABELS[compareA]} — Estatísticas
                </h3>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-muted text-xs">Mínimo</p>
                    <p className="text-text font-bold text-lg">{fmt(statsA.min)}</p>
                  </div>
                  <div>
                    <p className="text-muted text-xs">Máximo</p>
                    <p className="text-text font-bold text-lg">{fmt(statsA.max)}</p>
                  </div>
                  <div>
                    <p className="text-muted text-xs">Média</p>
                    <p className="text-text font-bold text-lg">{fmt(statsA.avg)}</p>
                  </div>
                  <div>
                    <p className="text-muted text-xs">Variação no período</p>
                    <p
                      className={`font-bold text-lg ${statsA.change >= 0 ? 'text-positive' : 'text-negative'}`}
                    >
                      {statsA.change >= 0 ? '+' : ''}
                      {fmt(statsA.change)}
                    </p>
                  </div>
                </div>
              </div>

              {/* Stats B */}
              <div className="bg-panel border border-border rounded-xl p-5">
                <h3 className="text-sm font-semibold mb-4" style={{ color: '#f97316' }}>
                  {INDICATOR_LABELS[compareB]} — Estatísticas
                </h3>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-muted text-xs">Mínimo</p>
                    <p className="text-text font-bold text-lg">{fmt(statsB.min)}</p>
                  </div>
                  <div>
                    <p className="text-muted text-xs">Máximo</p>
                    <p className="text-text font-bold text-lg">{fmt(statsB.max)}</p>
                  </div>
                  <div>
                    <p className="text-muted text-xs">Média</p>
                    <p className="text-text font-bold text-lg">{fmt(statsB.avg)}</p>
                  </div>
                  <div>
                    <p className="text-muted text-xs">Variação no período</p>
                    <p
                      className={`font-bold text-lg ${statsB.change >= 0 ? 'text-positive' : 'text-negative'}`}
                    >
                      {statsB.change >= 0 ? '+' : ''}
                      {fmt(statsB.change)}
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* ── Footer ── */}
      <footer className="border-t border-border mt-12 py-6 text-center text-muted text-xs">
        <p>Panorama BR · Dados: BCB, IBGE, B3 · Atualização automática a cada 5 minutos</p>
      </footer>
    </div>
  )
}
