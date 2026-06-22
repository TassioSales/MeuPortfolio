'use client'
import type { StockItem } from '@/lib/types'
import { fmt, changeColor, changeSign } from '@/lib/utils'

export default function StocksTable({ stocks }: { stocks: StockItem[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-muted border-b border-border">
            <th className="text-left py-3 px-2">Ativo</th>
            <th className="text-right py-3 px-2">Preço</th>
            <th className="text-right py-3 px-2">Variação</th>
            <th className="text-right py-3 px-2 hidden md:table-cell">Volume</th>
            <th className="text-right py-3 px-2 hidden lg:table-cell">Mkt Cap</th>
          </tr>
        </thead>
        <tbody>
          {stocks.map((s) => (
            <tr
              key={s.symbol}
              className="border-b border-border hover:bg-border/30 transition-colors"
            >
              <td className="py-3 px-2">
                <div className="font-semibold text-text">{s.symbol.replace('.SA', '')}</div>
                <div className="text-muted text-xs">{s.name}</div>
              </td>
              <td className="text-right py-3 px-2 font-mono">R$ {fmt(s.price)}</td>
              <td
                className={`text-right py-3 px-2 font-mono font-semibold ${changeColor(s.change_pct)}`}
              >
                {changeSign(s.change_pct)}
              </td>
              <td className="text-right py-3 px-2 text-muted hidden md:table-cell">
                {fmt(s.volume / 1e6, 1)}M
              </td>
              <td className="text-right py-3 px-2 text-muted hidden lg:table-cell">
                {fmt(s.market_cap / 1e9, 1)}bi
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
