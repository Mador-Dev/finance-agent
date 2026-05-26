import type { StrategyCatalyst } from "../../types/api";

const CATEGORY_ICON: Record<string, string> = {
  earnings: "📊",
  product: "🚀",
  regulatory: "⚖️",
  macro: "🌐",
  guidance: "🎯",
  other: "•",
};

const CATEGORY_LABEL: Record<string, string> = {
  earnings: "Earnings",
  product: "Product",
  regulatory: "Regulatory",
  macro: "Macro",
  guidance: "Guidance",
  other: "Other",
};

const IMPORTANCE_DOT: Record<string, { glyph: string; color: string }> = {
  high: { glyph: "●", color: "text-red-400" },
  medium: { glyph: "●", color: "text-amber-400" },
  low: { glyph: "●", color: "text-[var(--color-fg-subtle)]" },
};

function fmtDate(value: string | null | undefined): string {
  if (!value) return "";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function formatWindow(c: StrategyCatalyst): string {
  const end = c.windowEnd ?? c.expiresAt;
  const start = c.windowStart ?? null;
  if (!start && !end) return "—";
  if (start && end) return `${fmtDate(start)} → ${fmtDate(end)}`;
  if (end) return `by ${fmtDate(end)}`;
  return start ? `from ${fmtDate(start)}` : "—";
}

/**
 * Tight tabular display for a list of strategy catalysts.
 * Columns: Window · Catalyst · Importance · Status
 * Reused by the Reports feed modal and the portfolio Strategy modal so the
 * two surfaces always render catalysts the same way.
 */
export function CatalystTable({ catalysts }: { catalysts: StrategyCatalyst[] }) {
  if (!catalysts || catalysts.length === 0) return null;
  const now = new Date();
  return (
    <div className="overflow-hidden rounded-lg border border-[var(--color-border)]">
      <table className="w-full border-collapse text-[11px]">
        <thead>
          <tr className="bg-[var(--color-bg-muted)] text-[10px] uppercase tracking-wide text-[var(--color-fg-subtle)]">
            <th className="px-2 py-1.5 text-left font-medium">Window</th>
            <th className="px-2 py-1.5 text-left font-medium">Catalyst</th>
            <th className="px-1 py-1.5 text-center font-medium">Imp</th>
            <th className="px-1 py-1.5 text-center font-medium">Status</th>
          </tr>
        </thead>
        <tbody>
          {catalysts.map((c, i) => {
            const end = c.windowEnd ?? c.expiresAt;
            const expired = !c.triggered && end ? new Date(end) < now : false;
            const category = (c.category ?? "other") as keyof typeof CATEGORY_ICON;
            const importance = (c.importance ?? "medium") as keyof typeof IMPORTANCE_DOT;
            const imp = IMPORTANCE_DOT[importance];
            return (
              <tr
                key={`${c.description}-${i}`}
                className={`border-t border-[var(--color-border)] align-top ${
                  expired
                    ? "bg-red-500/4"
                    : c.triggered
                      ? "bg-emerald-500/4"
                      : "hover:bg-[var(--color-bg-muted)]/40"
                }`}
              >
                <td className="whitespace-nowrap px-2 py-1.5 font-mono text-[10px] text-[var(--color-fg-muted)]">
                  {formatWindow(c)}
                </td>
                <td className="px-2 py-1.5 text-[var(--color-fg-default)]">
                  <span
                    className="mr-1.5 inline-block"
                    title={CATEGORY_LABEL[category] ?? category}
                  >
                    {CATEGORY_ICON[category] ?? "•"}
                  </span>
                  {c.description}
                </td>
                <td className={`px-1 py-1.5 text-center ${imp.color}`} title={importance}>
                  {imp.glyph}
                </td>
                <td className="px-1 py-1.5 text-center">
                  {c.triggered ? (
                    <span className="text-emerald-400" title="Triggered">✓</span>
                  ) : expired ? (
                    <span className="text-red-400" title="Expired">⚠</span>
                  ) : (
                    <span className="text-[var(--color-fg-subtle)]" title="Pending">·</span>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
