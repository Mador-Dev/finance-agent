import { scoreBg, scoreBorder, scoreColor } from "../../utils/today/scoreColor";

interface HeroStatCardProps {
  value: string;
  pnlLine: string;
  pnlPositive: boolean | null;
  portfolioScore: number | null;
  /** Optional one-liner prose beneath the score bar (e.g., "Mostly on track…") */
  description?: string;
  /** Today's day-change % — rendered inline inside the card */
  todayPct?: number | null;
  /** Cumulative return % — rendered as "Total Return" inside the card */
  totalReturnPct?: number | null;
}

export function HeroStatCard({ value, pnlLine, pnlPositive, portfolioScore, description, todayPct, totalReturnPct }: HeroStatCardProps) {
  const hasScore = portfolioScore !== null && Number.isFinite(portfolioScore);
  const tintScore = hasScore ? (portfolioScore as number) : 70;

  const bg = hasScore ? scoreBg(tintScore) : "var(--bg-surface)";
  const border = hasScore ? scoreBorder(tintScore) : "var(--bg-border-mid)";
  const scoreTextColor = hasScore ? scoreColor(tintScore) : "var(--text-tertiary)";
  const scoreShadow = hasScore ? scoreBorder(tintScore) : "rgba(17, 24, 39, 0.18)";

  const pnlColor =
    pnlPositive === true
      ? "var(--color-green)"
      : pnlPositive === false
      ? "var(--color-red)"
      : "var(--text-secondary)";

  const todayColor =
    todayPct == null || todayPct === 0 ? "var(--text-tertiary)"
    : todayPct > 0 ? "var(--color-green)" : "var(--color-red)";
  const todayFmt =
    todayPct == null || todayPct === 0 ? "—"
    : `${todayPct >= 0 ? "+" : ""}${todayPct.toFixed(2)}%`;

  const retColor =
    totalReturnPct == null || totalReturnPct === 0 ? "var(--text-tertiary)"
    : totalReturnPct > 0 ? "var(--color-green)" : "var(--color-red)";
  const retFmt =
    totalReturnPct == null || totalReturnPct === 0 ? "—"
    : `${totalReturnPct >= 0 ? "+" : ""}${totalReturnPct.toFixed(2)}%`;

  return (
    <div
      style={{
        background: bg,
        border: `2px solid ${border}`,
        borderRadius: 22,
        padding: "18px 18px 16px",
        margin: "0 16px",
        boxShadow: `0 6px 0 ${scoreShadow}`,
        position: "relative",
      }}
    >

      {/* Top row: score ←→ value */}
      <div
        style={{
          display: "flex",
          alignItems: "stretch",
          justifyContent: "space-between",
          gap: 14,
          position: "relative",
          zIndex: 1,
        }}
      >
        {/* Left: label + total value + Today / Total Return */}
        <div>
          {/* "Portfolio Value" label */}
          <div
            style={{
              fontSize: 9,
              fontWeight: 600,
              textTransform: "uppercase",
              letterSpacing: "0.08em",
              color: "var(--text-tertiary)",
              marginBottom: 6,
            }}
          >
            Portfolio Value
          </div>
          {/* Cash amount */}
          <div
            style={{
              fontSize: 18,
              fontWeight: 700,
              lineHeight: 1,
              color: "var(--text-primary)",
              letterSpacing: "-0.5px",
              fontVariantNumeric: "tabular-nums",
            }}
          >
            {value}
          </div>
          {/* Today + Total Return — inline mini stats */}
          <div style={{ display: "flex", gap: 18, marginTop: 12 }}>
            <div>
              <div
                style={{
                  fontSize: 9,
                  fontWeight: 600,
                  textTransform: "uppercase",
                  letterSpacing: "0.07em",
                  color: "var(--text-tertiary)",
                  marginBottom: 3,
                }}
              >
                Today
              </div>
              <div
                style={{
                  fontSize: 12,
                  fontWeight: 700,
                  color: todayColor,
                  fontVariantNumeric: "tabular-nums",
                  letterSpacing: "-0.3px",
                }}
              >
                {todayFmt}
              </div>
            </div>
            <div>
              <div
                style={{
                  fontSize: 9,
                  fontWeight: 600,
                  textTransform: "uppercase",
                  letterSpacing: "0.07em",
                  color: "var(--text-tertiary)",
                  marginBottom: 3,
                }}
              >
                Total Return
              </div>
              <div
                style={{
                  fontSize: 12,
                  fontWeight: 700,
                  color: retColor,
                  fontVariantNumeric: "tabular-nums",
                  letterSpacing: "-0.3px",
                }}
              >
                {retFmt}
              </div>
            </div>
          </div>
        </div>

        {/* Right: score widget */}
        <div
          style={{
            minWidth: 108,
            alignSelf: "flex-start",
            background: "transparent",
            border: "0.5px solid var(--bg-border)",
            borderRadius: "var(--radius-xl)",
            padding: "10px 12px",
          }}
        >
          <div
            style={{
              fontSize: 32,
              lineHeight: 1,
              fontWeight: 800,
              fontVariantNumeric: "tabular-nums",
              letterSpacing: "-0.05em",
              color: hasScore ? scoreTextColor : "var(--text-ghost)",
            }}
          >
            {hasScore ? (portfolioScore as number) : "—"}
          </div>
          <div
            style={{
              marginTop: 7,
              display: "inline-flex",
              alignItems: "center",
              padding: "2px 8px",
              borderRadius: "var(--radius-pill)",
              background: "var(--bg-surface)",
              border: "0.5px solid var(--bg-border)",
              fontSize: "var(--text-2xs)",
              fontWeight: 700,
              color: hasScore ? scoreTextColor : "var(--text-tertiary)",
              textTransform: "uppercase",
              letterSpacing: "0.08em",
            }}
          >
            {hasScore ? (portfolioScore as number) >= 75 ? "Sharp" : (portfolioScore as number) >= 50 ? "Steady" : "Watchlist" : "Pending"}
          </div>
        </div>
      </div>

      {/* Score bar — 3px track */}
      <div style={{ marginTop: 16, position: "relative", zIndex: 1 }}>
        <div
          style={{
            position: "relative",
            height: 8,
            borderRadius: 999,
            background: "rgba(255,255,255,0.45)",
            overflow: "hidden",
            border: "1px solid rgba(17,24,39,0.08)",
          }}
        >
          <div
            style={{
              position: "absolute",
              insetInlineStart: 0,
              top: 0,
              bottom: 0,
              width: hasScore ? `${Math.max(0, Math.min(100, portfolioScore as number))}%` : "0%",
              background: scoreTextColor,
              borderRadius: 999,
              transition: "width 260ms ease",
            }}
          />
        </div>

        {/* Anchor labels */}
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            marginTop: 6,
            fontSize: 9,
            fontWeight: 700,
            color: "var(--text-tertiary)",
            textTransform: "uppercase",
            letterSpacing: "0.05em",
            fontVariantNumeric: "tabular-nums",
          }}
        >
          <span>0 rough</span>
          <span>50 steady</span>
          <span>100 golden</span>
        </div>
      </div>

      {/* Description prose — optional one-liner summary */}
      {description && (
        <p
          style={{
            margin: "12px 0 0",
            fontSize: "var(--text-sm)",
            lineHeight: 1.5,
            color: "var(--text-secondary)",
            fontWeight: 500,
            position: "relative",
            zIndex: 1,
          }}
        >
          {description}
        </p>
      )}
    </div>
  );
}

const SCORE_BAR_ANCHORS = [
  { at: 0, label: "exit" },
  { at: 50, label: "hold" },
  { at: 100, label: "strong buy" },
] as const;

interface ScoreBarProps {
  score: number;
}
export function ScoreBar({ score }: ScoreBarProps) {
  const pct = Math.max(0, Math.min(100, score));
  const color = scoreColor(score);
  return (
    <div style={{ padding: "0 16px" }}>
      <div
        style={{
          position: "relative",
          height: 6,
          borderRadius: 3,
          background: "rgba(255,255,255,0.07)",
          overflow: "hidden",
        }}
      >
        <div
          style={{
            position: "absolute",
            insetInlineStart: 0,
            top: 0,
            bottom: 0,
            width: `${pct}%`,
            background: color,
            borderRadius: 3,
            transition: "width 220ms ease",
          }}
        />
      </div>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          marginTop: 6,
          fontSize: 9,
          fontWeight: 400,
          color: "rgba(255,255,255,0.2)",
          textTransform: "lowercase",
          letterSpacing: "0.02em",
          fontVariantNumeric: "tabular-nums",
        }}
      >
        {SCORE_BAR_ANCHORS.map((a) => (
          <span key={a.at}>
            {a.at} {a.label}
          </span>
        ))}
      </div>
    </div>
  );
}
