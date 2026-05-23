import { scoreBg, scoreBorder, scoreColor } from "../../utils/today/scoreColor";

interface HeroStatCardProps {
  value: string;
  pnlLine: string;
  pnlPositive: boolean | null;
  portfolioScore: number | null;
  /** Optional one-liner prose beneath the score bar (e.g., "Mostly on track…") */
  description?: string;
}

export function HeroStatCard({ value, pnlLine, pnlPositive, portfolioScore, description }: HeroStatCardProps) {
  const hasScore = portfolioScore !== null && Number.isFinite(portfolioScore);
  const tintScore = hasScore ? (portfolioScore as number) : 70;

  const bg = hasScore ? scoreBg(tintScore) : "var(--bg-surface)";
  const border = hasScore ? scoreBorder(tintScore) : "var(--bg-border-mid)";
  const scoreTextColor = hasScore ? scoreColor(tintScore) : "var(--text-tertiary)";
  const scoreShadow = hasScore ? scoreBorder(tintScore) : "rgba(17, 24, 39, 0.18)";
  const stickerBg = hasScore ? "rgba(255,250,232,0.96)" : "rgba(255,255,255,0.92)";
  const stickerAccent = "rgba(17, 24, 39, 0.96)";

  const pnlColor =
    pnlPositive === true
      ? "var(--color-green)"
      : pnlPositive === false
      ? "var(--color-red)"
      : "var(--text-secondary)";

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
        overflow: "hidden",
      }}
    >
      <div
        aria-hidden="true"
        style={{
          position: "absolute",
          insetInlineEnd: -20,
          top: -26,
          width: 120,
          height: 120,
          borderRadius: "999px",
          background: "rgba(255,255,255,0.18)",
          filter: "blur(1px)",
        }}
      />

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
        {/* Left: total value + pnl */}
        <div>
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
          {pnlLine && (
            <div
              style={{
                fontSize: 10,
                fontWeight: 700,
                color: pnlColor,
                fontVariantNumeric: "tabular-nums",
                marginTop: 6,
                display: "inline-flex",
                alignItems: "center",
                gap: 6,
                padding: "4px 9px",
                borderRadius: 999,
                border: "1.5px solid rgba(17,24,39,0.12)",
                background: "rgba(255,255,255,0.72)",
              }}
            >
              {pnlLine}
            </div>
          )}
        </div>

        {/* Right: cartoon score sticker */}
        <div
          style={{
            minWidth: 124,
            alignSelf: "flex-start",
            background: stickerBg,
            border: `2.5px solid ${stickerAccent}`,
            borderRadius: 20,
            boxShadow: `5px 5px 0 rgba(34, 30, 26, 0.28)`,
            padding: "11px 12px 10px",
            transform: "rotate(1.5deg)",
          }}
        >
          <div
            style={{
              fontSize: 8,
              fontWeight: 800,
              color: "rgba(17, 24, 39, 0.78)",
              textTransform: "uppercase",
              letterSpacing: "0.12em",
              textAlign: "center",
            }}
          >
            Portfolio Score
          </div>
          <div
            style={{
              display: "flex",
              alignItems: "baseline",
              justifyContent: "center",
              gap: 4,
              marginTop: 6,
              color: stickerAccent,
            }}
          >
            <span
              style={{
                fontSize: 32,
                lineHeight: 1,
                fontWeight: 900,
                fontVariantNumeric: "tabular-nums",
                letterSpacing: "-0.06em",
                color: "rgba(17, 24, 39, 0.96)",
              }}
            >
              {hasScore ? (portfolioScore as number) : "—"}
            </span>
            <span style={{ fontSize: 12, lineHeight: 1, color: "#f59e0b" }}>★</span>
          </div>
          <div
            style={{
              marginTop: 4,
              textAlign: "center",
              fontSize: 10,
              fontWeight: 700,
              color: "rgba(17, 24, 39, 0.78)",
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
