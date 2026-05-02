"use client";

const COLORS = [
  "#ffffff",
  "#0f172a",
  "#ef4444",
  "#f97316",
  "#facc15",
  "#22c55e",
  "#14b8a6",
  "#22d3ee",
  "#3b82f6",
  "#8b5cf6",
  "#ec4899",
  "#fb7185",
];

type ColorPaletteProps = {
  selectedColor: string;
  onSelect: (color: string) => void;
};

export function ColorPalette({ selectedColor, onSelect }: ColorPaletteProps) {
  return (
    <div className="grid grid-cols-6 gap-2">
      {COLORS.map((color) => (
        <button
          aria-label={`Select ${color}`}
          className="h-9 rounded-md border transition hover:scale-105 focus:outline-none focus:ring-2 focus:ring-cyan-300"
          key={color}
          onClick={() => onSelect(color)}
          style={{
            backgroundColor: color,
            borderColor: selectedColor === color ? "#22d3ee" : "rgba(148, 163, 184, 0.28)",
            boxShadow: selectedColor === color ? "0 0 18px rgba(34, 211, 238, 0.42)" : "none",
          }}
          type="button"
        />
      ))}
    </div>
  );
}
