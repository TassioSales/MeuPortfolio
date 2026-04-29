import { Card } from "@/components/ui/card";
import { FuelSummary } from "@/lib/types";

const statePositions: Record<string, { x: number; y: number; labelX?: number; labelY?: number }> = {
  AC: { x: 94, y: 228, labelX: 70, labelY: 228 },
  AL: { x: 416, y: 218, labelX: 434, labelY: 223 },
  AM: { x: 138, y: 154, labelX: 108, labelY: 146 },
  AP: { x: 286, y: 88, labelX: 302, labelY: 72 },
  BA: { x: 374, y: 246, labelX: 392, labelY: 256 },
  CE: { x: 414, y: 172, labelX: 442, labelY: 170 },
  DF: { x: 314, y: 252, labelX: 332, labelY: 248 },
  ES: { x: 388, y: 304, labelX: 410, labelY: 312 },
  GO: { x: 294, y: 264, labelX: 268, labelY: 278 },
  MA: { x: 344, y: 164, labelX: 324, labelY: 150 },
  MG: { x: 348, y: 292, labelX: 324, labelY: 306 },
  MS: { x: 242, y: 314, labelX: 212, labelY: 324 },
  MT: { x: 228, y: 236, labelX: 194, labelY: 240 },
  PA: { x: 278, y: 148, labelX: 246, labelY: 138 },
  PB: { x: 444, y: 186, labelX: 466, labelY: 188 },
  PE: { x: 434, y: 206, labelX: 454, labelY: 208 },
  PI: { x: 372, y: 182, labelX: 390, labelY: 190 },
  PR: { x: 304, y: 358, labelX: 282, labelY: 374 },
  RJ: { x: 372, y: 326, labelX: 394, labelY: 334 },
  RN: { x: 452, y: 160, labelX: 474, labelY: 156 },
  RO: { x: 166, y: 244, labelX: 142, labelY: 258 },
  RR: { x: 184, y: 78, labelX: 160, labelY: 58 },
  RS: { x: 312, y: 444, labelX: 292, labelY: 462 },
  SC: { x: 318, y: 398, labelX: 338, labelY: 406 },
  SE: { x: 404, y: 228, labelX: 424, labelY: 238 },
  SP: { x: 316, y: 332, labelX: 340, labelY: 344 },
  TO: { x: 304, y: 194, labelX: 286, labelY: 176 },
};

const brazilPath =
  "M183 55 L214 63 L236 82 L258 84 L279 112 L305 117 L329 137 L363 142 L392 164 L435 157 L454 177 L451 203 L423 216 L430 243 L413 267 L396 273 L390 305 L368 326 L355 352 L338 350 L323 368 L322 401 L308 433 L287 421 L279 392 L262 370 L240 367 L230 343 L206 324 L206 286 L186 258 L162 259 L146 236 L118 223 L103 188 L110 164 L128 140 L127 112 L149 91 L170 89 L177 69 Z";

function colorForPrice(price: number) {
  if (price >= 6.3) return "#ff7b72";
  if (price >= 6.0) return "#f4b860";
  return "#36d6a7";
}

function markerRadius(price: number) {
  if (price >= 6.3) return 9;
  if (price >= 6.0) return 7.5;
  return 6.5;
}

function labelForPrice(price: number) {
  if (price >= 6.3) return "Alta";
  if (price >= 6.0) return "Media";
  return "Baixa";
}

export function PriceMap({ data }: { data: FuelSummary[] }) {
  const visibleData = data.filter((item) => statePositions[item.state]);
  const topThree = visibleData.slice().sort((a, b) => b.average_price - a.average_price).slice(0, 3);

  return (
    <Card className="overflow-hidden bg-[linear-gradient(180deg,rgba(54,214,167,0.08),rgba(255,255,255,0.02))]">
      <div className="flex h-full flex-col">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-[10px] uppercase font-bold tracking-[0.4em] text-mist/50">Geographical Intel</p>
            <h3 className="mt-3 font-display text-4xl leading-tight">Mapa de Precos</h3>
            <p className="mt-3 max-w-xl text-sm leading-7 text-mist">
              O mapa agora ocupa quase todo o painel, com silhueta forte, intensidade visual por preco e leitura territorial mais clara.
            </p>
          </div>
          <div className="rounded-full border border-accent/20 bg-accent/10 px-3 py-1 text-[10px] uppercase tracking-[0.24em] text-accent">Brasil</div>
        </div>

        <div className="mt-6 grid gap-4">
          <div className="relative min-h-[620px] rounded-[2rem] border border-white/10 bg-[radial-gradient(circle_at_center,rgba(15,23,42,0.95),rgba(2,6,23,1)),radial-gradient(circle_at_top,rgba(107,184,255,0.16),transparent_28%),radial-gradient(circle_at_bottom,rgba(54,214,167,0.12),transparent_28%)] p-5 shadow-[inset_0_1px_0_rgba(255,255,255,0.06)] lg:min-h-[720px]">
            <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(255,255,255,0.02),transparent_45%)]" />
            <svg viewBox="0 0 520 500" className="mx-auto h-full w-full max-w-[1000px]">
              <defs>
                <filter id="mapGlow" x="-50%" y="-50%" width="200%" height="200%">
                  <feGaussianBlur stdDeviation="8" result="blur" />
                  <feMerge>
                    <feMergeNode in="blur" />
                    <feMergeNode in="SourceGraphic" />
                  </feMerge>
                </filter>
                <radialGradient id="territoryGlow" cx="50%" cy="45%" r="62%">
                  <stop offset="0%" stopColor="rgba(107,184,255,0.12)" />
                  <stop offset="100%" stopColor="rgba(107,184,255,0)" />
                </radialGradient>
              </defs>

              <rect x="0" y="0" width="520" height="500" fill="url(#territoryGlow)" />

              <path
                d={brazilPath}
                fill="rgba(107,184,255,0.1)"
                stroke="rgba(107,184,255,0.34)"
                strokeWidth="2.8"
              />

              <path
                d={brazilPath}
                fill="none"
                stroke="rgba(255,255,255,0.1)"
                strokeWidth="18"
                filter="url(#mapGlow)"
              />

              {visibleData.map((item) => {
                const pos = statePositions[item.state];
                const fill = colorForPrice(item.average_price);
                const radius = markerRadius(item.average_price);
                const labelX = pos.labelX ?? pos.x + 14;
                const labelY = pos.labelY ?? pos.y - 12;

                return (
                  <g key={item.state} className="group cursor-pointer">
                    <line
                      x1={pos.x}
                      y1={pos.y}
                      x2={labelX}
                      y2={labelY}
                      stroke="rgba(255,255,255,0.16)"
                      strokeWidth="1"
                      strokeDasharray="4 4"
                    />
                    <circle cx={pos.x} cy={pos.y} r={radius + 12} fill={fill} opacity="0.08">
                      <animate attributeName="r" values={`${radius + 7};${radius + 11};${radius + 7}`} dur="2.4s" repeatCount="indefinite" />
                      <animate attributeName="opacity" values="0.08;0.18;0.08" dur="2.4s" repeatCount="indefinite" />
                    </circle>
                    <circle cx={pos.x} cy={pos.y} r={radius + 3.5} fill={fill} opacity="0.16" />
                    <circle cx={pos.x} cy={pos.y} r={radius} fill={fill} stroke="#08111a" strokeWidth="2.5" />
                    <circle cx={pos.x} cy={pos.y} r="1.7" fill="#ffffff" opacity="0.8" />

                    <g transform={`translate(${labelX}, ${labelY})`}>
                      <rect
                        x="-12"
                        y="-10"
                        rx="8"
                        width="36"
                        height="20"
                        fill="rgba(8,17,26,0.92)"
                        stroke="rgba(255,255,255,0.12)"
                      />
                      <text
                        x="6"
                        y="3"
                        textAnchor="middle"
                        className="fill-white text-[8px] font-bold tracking-[0.12em]"
                      >
                        {item.state}
                      </text>
                    </g>

                    <g className="opacity-0 transition-opacity group-hover:opacity-100">
                      <rect
                        x={pos.x + 10}
                        y={pos.y - 46}
                        rx="10"
                        width="78"
                        height="34"
                        fill="rgba(8,17,26,0.95)"
                        stroke="rgba(255,255,255,0.12)"
                      />
                      <text x={pos.x + 49} y={pos.y - 29} textAnchor="middle" className="fill-white text-[9px] font-bold">
                        {item.average_price.toFixed(2)}
                      </text>
                      <text x={pos.x + 49} y={pos.y - 17} textAnchor="middle" className="fill-[#8ea4b8] text-[7px]">
                        {labelForPrice(item.average_price)}
                      </text>
                    </g>
                  </g>
                );
              })}
            </svg>
          </div>

          <div className="grid gap-3 lg:grid-cols-3">
            <div className="rounded-[1.5rem] border border-white/10 bg-black/20 p-4">
              <p className="text-[10px] uppercase tracking-[0.24em] text-white/45">Escala de calor</p>
              <div className="mt-4 rounded-full h-3 w-full bg-[linear-gradient(90deg,#36d6a7_0%,#f4b860_50%,#ff7b72_100%)]" />
              <div className="mt-3 flex justify-between text-[11px] text-mist">
                <span>Baixo</span>
                <span>Medio</span>
                <span>Alto</span>
              </div>
              <div className="mt-4 space-y-2 text-xs text-mist">
                <p>Verde: abaixo de R$ 6,00</p>
                <p>Amarelo: entre R$ 6,00 e R$ 6,29</p>
                <p>Vermelho: acima de R$ 6,30</p>
              </div>
            </div>

            <div className="rounded-[1.5rem] border border-white/10 bg-black/20 p-4">
              <p className="text-[10px] uppercase tracking-[0.24em] text-white/45">Leitura</p>
              <p className="mt-4 text-sm leading-7 text-mist">
                O tamanho do marcador cresce com o preco e o pulso suave destaca os pontos com maior intensidade visual.
              </p>
            </div>

            <div className="rounded-[1.5rem] border border-white/10 bg-black/20 p-4">
              <p className="text-[10px] uppercase tracking-[0.24em] text-white/45">Maiores precos</p>
              <div className="mt-4 space-y-3">
                {topThree.map((item, index) => (
                  <div key={`${item.state}-${index}`} className="flex items-center justify-between rounded-2xl border border-white/8 bg-white/[0.04] px-3 py-3">
                    <div>
                      <p className="text-sm text-white">{item.state}</p>
                      <p className="text-[11px] text-mist">{labelForPrice(item.average_price)}</p>
                    </div>
                    <p className="font-display text-xl text-white">R$ {item.average_price.toFixed(2)}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </Card>
  );
}
