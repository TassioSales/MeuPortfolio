"use client";
import { motion } from "framer-motion";
import type { Milestone } from "@/lib/api";

interface Props {
  milestones: Milestone[];
  currentIndex: number;
  progressPct: number;
}

// Wider viewBox so labels have room
const VIEW_W = 760;
const VIEW_H = 340;

// Positions spread across the SVG — gentle S-curve
const POSITIONS = [
  { x: 80,  y: 260 },
  { x: 215, y: 195 },
  { x: 365, y: 148 },
  { x: 515, y: 100 },
  { x: 660, y: 60  },
];

function buildPath(pts: { x: number; y: number }[]): string {
  if (pts.length < 2) return "";
  let d = `M ${pts[0].x} ${pts[0].y}`;
  for (let i = 1; i < pts.length; i++) {
    const p = pts[i - 1];
    const c = pts[i];
    const cpx = (p.x + c.x) / 2;
    d += ` C ${cpx} ${p.y} ${cpx} ${c.y} ${c.x} ${c.y}`;
  }
  return d;
}

function truncate(s: string, n: number) {
  return s.length > n ? s.slice(0, n - 1) + "…" : s;
}

export function CareerPath({ milestones, currentIndex, progressPct }: Props) {
  const pts = POSITIONS.slice(0, milestones.length);
  const pathD = buildPath(pts);
  const DASH_TOTAL = 1100;
  const drawn = (progressPct / 100) * DASH_TOTAL;

  return (
    <svg
      viewBox={`0 0 ${VIEW_W} ${VIEW_H}`}
      className="w-full h-full"
      style={{ overflow: "visible" }}
    >
      <defs>
        <linearGradient id="pathGrad" x1="0%" y1="100%" x2="100%" y2="0%">
          <stop offset="0%" stopColor="#00e87a" stopOpacity="0.25" />
          <stop offset="100%" stopColor="#00e87a" stopOpacity="1" />
        </linearGradient>
        <filter id="glow" x="-30%" y="-30%" width="160%" height="160%">
          <feGaussianBlur stdDeviation="3.5" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
        <filter id="glowSm" x="-20%" y="-20%" width="140%" height="140%">
          <feGaussianBlur stdDeviation="2" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>

      {/* Track */}
      <path d={pathD} fill="none" stroke="#1e2536" strokeWidth="3" strokeLinecap="round" />

      {/* Animated progress */}
      <motion.path
        d={pathD}
        fill="none"
        stroke="url(#pathGrad)"
        strokeWidth="3"
        strokeLinecap="round"
        filter="url(#glow)"
        initial={{ strokeDasharray: DASH_TOTAL, strokeDashoffset: DASH_TOTAL }}
        animate={{ strokeDashoffset: DASH_TOTAL - drawn }}
        transition={{ duration: 1.8, ease: "easeOut" }}
      />

      {pts.map((pos, i) => {
        const ms = milestones[i];
        const done = i < currentIndex;
        const active = i === currentIndex;
        // Labels alternate: odd nodes get label below the node, even above
        const labelAbove = i % 2 === 0;
        const labelY = labelAbove ? pos.y - 52 : pos.y + 28;
        const LABEL_W = 130;
        const LABEL_H = 30;

        return (
          <g key={i}>
            {/* Pulse ring for active node */}
            {active && (
              <motion.circle
                cx={pos.x} cy={pos.y} r={22}
                fill="none"
                stroke="#00e87a"
                strokeWidth="1.5"
                initial={{ opacity: 0 }}
                animate={{ r: [16, 26, 16], opacity: [0.5, 0, 0.5] }}
                transition={{ repeat: Infinity, duration: 2.4, ease: "easeInOut" }}
              />
            )}

            {/* Connector line from node to label */}
            {ms?.title && (
              <line
                x1={pos.x}
                y1={pos.y + (labelAbove ? -13 : 13)}
                x2={pos.x}
                y2={labelAbove ? labelY + LABEL_H : labelY}
                stroke={active ? "#00e87a" : done ? "#00e87a" : "#252d40"}
                strokeWidth="1"
                strokeOpacity={active || done ? 0.4 : 0.3}
                strokeDasharray="3 3"
              />
            )}

            {/* Node circle */}
            <circle
              cx={pos.x} cy={pos.y} r={13}
              fill={done ? "#00e87a" : active ? "#0f1219" : "#161b27"}
              stroke={done || active ? "#00e87a" : "#252d40"}
              strokeWidth={active ? 2.5 : 1.5}
              filter={active || done ? "url(#glowSm)" : undefined}
            />

            {/* Check mark for done */}
            {done && (
              <text
                x={pos.x} y={pos.y + 4.5}
                textAnchor="middle"
                fontSize="11"
                fill="#0f1219"
                fontWeight="bold"
              >
                ✓
              </text>
            )}

            {/* Active center dot */}
            {active && (
              <circle cx={pos.x} cy={pos.y} r={4} fill="#00e87a" />
            )}

            {/* Step number for not started */}
            {!done && !active && (
              <text
                x={pos.x} y={pos.y + 4.5}
                textAnchor="middle"
                fontSize="10"
                fill="#3d4a66"
                fontWeight="700"
              >
                {i + 1}
              </text>
            )}

            {/* Label box */}
            {ms?.title && (
              <>
                <rect
                  x={pos.x - LABEL_W / 2}
                  y={labelY}
                  width={LABEL_W}
                  height={LABEL_H}
                  rx={6}
                  fill={active ? "rgba(0,232,122,0.1)" : done ? "rgba(0,232,122,0.06)" : "rgba(22,27,39,0.9)"}
                  stroke={active ? "rgba(0,232,122,0.4)" : done ? "rgba(0,232,122,0.25)" : "#252d40"}
                  strokeWidth={active ? 1.2 : 0.8}
                />
                <text
                  x={pos.x}
                  y={labelY + LABEL_H / 2 + 4.5}
                  textAnchor="middle"
                  fontSize="11.5"
                  fill={active ? "#00e87a" : done ? "#c8ffe0" : "#8892b0"}
                  fontWeight={active ? "700" : done ? "600" : "400"}
                >
                  {truncate(ms.title, 17)}
                </text>
              </>
            )}
          </g>
        );
      })}

      {/* "Meta de carreira" badge at last node */}
      {pts.length > 0 && (
        <g>
          <rect
            x={pts[pts.length - 1].x - 58}
            y={pts[pts.length - 1].y - 52}
            width={116}
            height={26}
            rx={7}
            fill="rgba(0,232,122,0.12)"
            stroke="#00e87a"
            strokeWidth={1}
          />
          <text
            x={pts[pts.length - 1].x}
            y={pts[pts.length - 1].y - 34}
            textAnchor="middle"
            fontSize="11"
            fill="#00e87a"
            fontWeight="600"
          >
            ★ Meta de carreira
          </text>
        </g>
      )}
    </svg>
  );
}
