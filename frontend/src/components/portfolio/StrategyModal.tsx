import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, ArrowRight, Check, Circle, AlertTriangle } from "lucide-react";
import { fetchStrategy } from "../../api/strategies";
import { triggerJob } from "../../api/jobs";
import { Spinner } from "../ui/Spinner";
import { ErrorState } from "../ui/ErrorState";
import { ActionBadge } from "../design/ActionBadge";
import { StatCell } from "../design/StatCell";
import { ScoreBar } from "../design/HeroStatCard";
import { useToastStore } from "../../store/toastStore";
import { usePreferencesStore } from "../../store/preferencesStore";
import { t, tConfidence } from "../../store/i18n";
import { formatILS, timeAgo } from "../../utils/format";

import {
  verdictSentence,
  scoreBucketLabel,
  scoreBucketEmoji,
  formatCatalyst,
  nextCatalyst,
  reasoningSnippet,
} from "../../utils/advisory";
import { CatalystTable } from "../strategy/CatalystTable";
import type { StrategyRow, PositionRow, Verdict, VerdictRow } from "../../types/api";
import { ThesisSection } from "./ThesisSection";
import { ScoreBreakdown } from "./ScoreBreakdown";
import { usePositionGuidance } from "../../hooks/usePositionGuidance";
import { healthScore, DEFAULT_STOP_LOSS_PCT } from "../../utils/today/healthScore";

interface StrategyModalProps {
  ticker: string | null;
  score?: number;
  position?: PositionRow | null;
  onClose: () => void;
  onDeepDive?: (ticker: string) => void;
}


/** Primary CTA label per verdict. HOLD → undefined = no primary button shown. */
const VERDICT_CTA: Partial<Record<Verdict, string>> = {
  REDUCE: "Deep dive before trimming",
  SELL: "Deep dive before exiting",
  CLOSE: "Deep dive before exiting",
  BUY: "Deep dive before adding",
  ADD: "Deep dive before adding",
};

function ctaBg(verdict: Verdict): string {
  switch (verdict) {
    case "BUY": case "ADD":    return "var(--color-green-bg)";
    case "REDUCE":             return "var(--color-amber-bg)";
    case "SELL": case "CLOSE": return "var(--color-red-bg)";
    default:                   return "var(--bg-surface)";
  }
}
function ctaFg(verdict: Verdict): string {
  switch (verdict) {
    case "BUY": case "ADD":    return "var(--color-green)";
    case "REDUCE":             return "var(--color-amber)";
    case "SELL": case "CLOSE": return "var(--color-red)";
    default:                   return "var(--text-primary)";
  }
}
function ctaBorder(verdict: Verdict): string {
  switch (verdict) {
    case "BUY": case "ADD":    return "var(--color-green-border)";
    case "REDUCE":             return "var(--color-amber-border)";
    case "SELL": case "CLOSE": return "var(--color-red-border)";
    default:                   return "var(--bg-border)";
  }
}

export function StrategyModal({
  ticker,
  score,
  position,
  onClose,
  onDeepDive,
}: StrategyModalProps) {
  const language = usePreferencesStore((s) => s.language);
  const showToast = useToastStore((s) => s.show);
  const queryClient = useQueryClient();

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["strategy", ticker],
    queryFn: () => fetchStrategy(ticker!),
    enabled: !!ticker,
  });

  const handleDeepDive = async () => {
    if (!ticker) return;
    try {
      await triggerJob("deep_dive", ticker);
      await queryClient.invalidateQueries({ queryKey: ["balance"] });
      showToast(`${t("jobDeepDiveTitle", language)} — ${ticker} ${t("jobQueued", language)}`, "success");
      onDeepDive?.(ticker);
    } catch (err) {
      const apiError = err as { response?: { data?: { reason?: string; error?: string } } };
      showToast(apiError.response?.data?.reason ?? t("jobFailed", language), "error");
    }
  };

  if (!ticker) return null;

  const verdictType = data?.verdict;
  const ctaLabel = verdictType ? (VERDICT_CTA[verdictType] ?? null) : null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      onClick={(e) => e.target === e.currentTarget && onClose()}
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 50,
        background: "rgba(0,0,0,0.65)",
        backdropFilter: "blur(4px)",
        display: "flex",
        alignItems: "flex-start",
        justifyContent: "center",
        padding: "12px",
      }}
    >
      <div
        style={{
          width: "100%",
          maxWidth: 560,
          maxHeight: "calc(100vh - 24px)",
          background: "var(--bg-base)",
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
          borderRadius: 16,
          border: "1px solid rgba(255,255,255,0.18)",
          boxShadow: "0 0 0 1px rgba(255,255,255,0.06), 0 24px 80px rgba(0,0,0,0.85), 0 8px 32px rgba(0,0,0,0.6)",
        }}
      >
        {/* Header */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 12,
            padding: "12px 16px",
            borderBottom: "0.5px solid var(--bg-border)",
            flexShrink: 0,
          }}
        >
          <button
            type="button"
            onClick={onClose}
            aria-label={language === "he" ? "חזור" : "Back"}
            style={{
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              width: 32,
              height: 32,
              borderRadius: "var(--radius-sm)",
              background: "transparent",
              border: "none",
              color: "var(--text-secondary)",
              cursor: "pointer",
            }}
          >
            {language === "he" ? <ArrowRight size={18} /> : <ArrowLeft size={18} />}
          </button>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div
              style={{
                fontSize: "var(--text-md)",
                fontWeight: "var(--weight-bold)",
                color: "var(--text-primary)",
                fontFamily: "ui-monospace, SFMono-Regular, monospace",
              }}
            >
              {ticker}
            </div>
            {position && (
              <div style={{ fontSize: "var(--text-2xs)", color: "var(--text-tertiary)" }}>
                {position.exchange === "TASE" ? "Tel Aviv Stock Exchange" : position.exchange}
              </div>
            )}
          </div>
          {data && <ActionBadge verdict={data.verdict} score={score} />}
        </div>

        {/* Scrollable body */}
        <div style={{ flex: 1, overflowY: "auto" }}>
          {isLoading && (
            <div style={{ display: "flex", justifyContent: "center", padding: "48px 0" }}>
              <Spinner size="lg" />
            </div>
          )}
          {error && (
            <ErrorState message={t("failedLoadStrategy", language)} onRetry={() => refetch()} />
          )}
          {data && (
            <DetailContent
              strategy={data}
              ticker={ticker}
              score={score}
              position={position ?? null}
              language={language}
            />
          )}
        </div>

        {/* Footer — verdict-aware: no primary CTA for HOLD */}
        {data && (
          <div
            style={{
              display: "flex",
              gap: 8,
              padding: "12px 16px calc(12px + env(safe-area-inset-bottom))",
              borderTop: "0.5px solid var(--bg-border)",
              background: "var(--bg-base)",
              flexShrink: 0,
            }}
          >
            {ctaLabel && verdictType && (
              <button
                type="button"
                onClick={handleDeepDive}
                aria-label={`${ctaLabel} for ${ticker}`}
                style={{
                  flex: 1,
                  padding: "12px",
                  borderRadius: "var(--radius-md)",
                  background: ctaBg(verdictType),
                  color: ctaFg(verdictType),
                  border: `0.5px solid ${ctaBorder(verdictType)}`,
                  fontSize: "var(--text-sm)",
                  fontWeight: "var(--weight-bold)",
                  cursor: "pointer",
                }}
              >
                {ctaLabel}
              </button>
            )}
            <button
              type="button"
              onClick={onClose}
              style={{
                flex: ctaLabel ? 0 : 1,
                padding: "12px 20px",
                borderRadius: "var(--radius-md)",
                background: "transparent",
                color: "var(--text-secondary)",
                border: "0.5px solid var(--bg-border)",
                fontSize: "var(--text-sm)",
                fontWeight: "var(--weight-regular)",
                cursor: "pointer",
                whiteSpace: "nowrap",
              }}
            >
              {language === "he" ? "סגור" : "Close"}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

function verdictFg(verdict: Verdict): string {
  switch (verdict) {
    case "BUY": case "ADD":    return "var(--color-green)";
    case "REDUCE":             return "var(--color-amber)";
    case "SELL": case "CLOSE": return "var(--color-red)";
    default:                   return "var(--text-primary)";
  }
}

function MetaPill({ label, value }: { label: string; value: string }) {
  return (
    <div
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 5,
        padding: "3px 10px",
        background: "var(--bg-surface)",
        border: "0.5px solid var(--bg-border)",
        borderRadius: "var(--radius-pill)",
      }}
    >
      <span
        style={{
          fontSize: "var(--text-2xs)",
          color: "var(--text-tertiary)",
          textTransform: "uppercase",
          letterSpacing: "0.06em",
          fontWeight: 400,
        }}
      >
        {label}
      </span>
      <span
        style={{
          fontSize: "var(--text-xs)",
          color: "var(--text-secondary)",
          fontWeight: "var(--weight-bold)",
        }}
      >
        {value}
      </span>
    </div>
  );
}

function DetailContent({
  strategy,
  ticker,
  score,
  position,
  language,
}: {
  strategy: StrategyRow;
  ticker: string | null;
  score?: number;
  position: PositionRow | null;
  language: "en" | "he";
}) {
  const { guidanceMap, updateGuidance } = usePositionGuidance();
  const verdictLine = verdictSentence(strategy.verdict);
  const heroScore = score ?? 0;
  const hasScore = score !== undefined && Number.isFinite(score);

  const scoreBreakdown = hasScore
    ? healthScore(strategy as unknown as VerdictRow, position ?? undefined, DEFAULT_STOP_LOSS_PCT).breakdown
    : null;

  const dayChangePct = position?.dayChangePct ?? 0;
  const dayChangeILS = position?.dayChangeILS ?? 0;
  const hasDay = dayChangePct !== 0;

  const timeframeLabel =
    strategy.timeframe && strategy.timeframe !== "undefined"
      ? strategy.timeframe.replace(/_/g, " ")
      : null;

  const totalConditions = strategy.entryConditions.length + strategy.exitConditions.length;

  return (
    <div>

      {/* ─── Verdict block ─── */}
      <div style={{ padding: "20px 16px 16px" }}>

        {/* Verdict field label */}
        <div
          style={{
            fontSize: "var(--text-2xs)",
            textTransform: "uppercase",
            letterSpacing: "0.06em",
            color: "var(--text-tertiary)",
            fontWeight: 400,
            marginBottom: 6,
          }}
        >
          {language === "he" ? "המלצה" : "Verdict"}
        </div>

        {/* Verdict keyword + sentence + timestamp */}
        <div
          style={{
            display: "flex",
            alignItems: "flex-start",
            justifyContent: "space-between",
            gap: 12,
            marginBottom: 10,
          }}
        >
          <div>
            <div style={{ display: "flex", alignItems: "baseline", gap: 10, marginBottom: 4 }}>
              <span
                style={{
                  fontSize: "var(--text-xl)",
                  fontWeight: "var(--weight-bold)",
                  color: verdictFg(strategy.verdict),
                  fontFamily: "ui-monospace, SFMono-Regular, monospace",
                  letterSpacing: "-0.5px",
                }}
              >
                {strategy.verdict}
              </span>
              <span
                style={{
                  fontSize: "var(--text-md)",
                  color: "var(--text-secondary)",
                  lineHeight: 1.4,
                  fontWeight: "var(--weight-regular)",
                }}
              >
                {verdictLine}
              </span>
            </div>
          </div>
          <span
            style={{
              fontSize: "var(--text-2xs)",
              color: "var(--text-tertiary)",
              whiteSpace: "nowrap",
              paddingTop: 4,
              flexShrink: 0,
            }}
          >
            {timeAgo(strategy.updatedAt)}
          </span>
        </div>

        {/* Meta pills — confidence · horizon */}
        <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
          <MetaPill
            label={language === "he" ? "ביטחון" : "Confidence"}
            value={tConfidence(strategy.confidence, language)}
          />
          {timeframeLabel && (
            <MetaPill
              label={language === "he" ? "אופק" : "Horizon"}
              value={timeframeLabel}
            />
          )}
          {hasScore && (
            <MetaPill
              label={language === "he" ? "ניקוד" : "Score"}
              value={`${heroScore} · ${scoreBucketEmoji(heroScore)} ${scoreBucketLabel(heroScore)}`}
            />
          )}
        </div>
      </div>

      {/* Score bar + breakdown */}
      {hasScore && (
        <div style={{ paddingBottom: scoreBreakdown ? 4 : 0 }}>
          <ScoreBar score={heroScore} />
        </div>
      )}
      {hasScore && scoreBreakdown && (
        <ScoreBreakdown breakdown={scoreBreakdown} score={heroScore} />
      )}

      <Divider />

      {/* ─── Analysis ─── */}
      {strategy.reasoning && (
        <>
          <SectionHeader
            label={language === "he" ? "ניתוח" : "Analysis"}
          />
          <p
            style={{
              padding: "0 16px 16px",
              margin: 0,
              fontSize: "var(--text-md)",
              lineHeight: 1.6,
              color: "var(--text-secondary)",
              fontWeight: "var(--weight-regular)",
            }}
          >
            {strategy.reasoning}
          </p>
        </>
      )}

      {/* ─── Bull / Bear ─── */}
      {(strategy.bullCase || strategy.bearCase) && (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: 8,
            padding: "0 16px 16px",
          }}
        >
          <BullBearCard
            kind="bull"
            label={language === "he" ? "בעד" : "Bull case"}
            text={strategy.bullCase}
          />
          <BullBearCard
            kind="bear"
            label={language === "he" ? "נגד" : "Bear case"}
            text={strategy.bearCase}
          />
        </div>
      )}

      {/* ─── Catalysts — structured table ─── */}
      {(strategy.catalysts ?? []).length > 0 && (
        <div style={{ margin: "0 16px 16px" }}>
          <div
            style={{
              fontSize: "var(--text-2xs)",
              fontWeight: "var(--weight-bold)",
              color: "var(--text-secondary)",
              textTransform: "uppercase",
              letterSpacing: "0.06em",
              marginBottom: 6,
            }}
          >
            {language === "he"
              ? `קטליסטים (${strategy.catalysts!.length})`
              : `Catalysts (${strategy.catalysts!.length})`}
          </div>
          <CatalystTable catalysts={strategy.catalysts ?? []} />
        </div>
      )}

      <Divider />

      {/* ─── Conditions — exit first (most actionable), then entry ─── */}
      <SectionHeader
        label={language === "he" ? "תנאים" : "Conditions"}
        meta={totalConditions > 0 ? `${totalConditions} active` : undefined}
      />
      <div style={{ padding: "0 16px 20px" }}>
        {strategy.exitConditions.map((c, i) => (
          <ConditionRow
            key={`x-${i}`}
            kind="exit"
            text={c}
            label={language === "he" ? "יציאה" : "EXIT"}
            verdict={strategy.verdict}
          />
        ))}
        {strategy.entryConditions.map((c, i) => (
          <ConditionRow
            key={`e-${i}`}
            kind="entry"
            text={c}
            label={language === "he" ? "כניסה" : "ENTRY"}
            verdict={strategy.verdict}
          />
        ))}
        {totalConditions === 0 && (
          <div style={{ fontSize: "var(--text-sm)", color: "var(--text-tertiary)" }}>
            {language === "he" ? "אין תנאים מוגדרים" : "No conditions set."}
          </div>
        )}
      </div>

      {/* ─── Your position stats (only if position data available) ─── */}
      {position && (
        <>
          <Divider />
          <SectionHeader label={language === "he" ? "הפוזיציה שלך" : "Your position"} />
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: 8,
              padding: "0 16px 16px",
            }}
          >
            <StatCell
              label={language === "he" ? "משקל" : "Weight"}
              value={`${(strategy.positionWeightPct ?? position.weightPct ?? 0).toFixed(1)}%`}
              sub="of portfolio"
            />
            <StatCell
              label={language === "he" ? "רווח / הפסד" : "P / L"}
              value={`${position.plPct >= 0 ? "+" : ""}${position.plPct.toFixed(1)}%`}
              sub={
                position.plILS !== 0
                  ? `${position.plILS >= 0 ? "+" : ""}${formatILS(Math.abs(position.plILS))}`
                  : undefined
              }
              positive={position.plPct > 0 ? true : position.plPct < 0 ? false : null}
            />
            <StatCell
              label={language === "he" ? "היום" : "Today"}
              value={hasDay ? `${dayChangePct >= 0 ? "+" : ""}${dayChangePct.toFixed(2)}%` : "—"}
              sub={
                hasDay && dayChangeILS !== 0
                  ? `${dayChangeILS >= 0 ? "+" : ""}${formatILS(Math.abs(dayChangeILS))}`
                  : undefined
              }
              positive={hasDay ? dayChangePct > 0 : null}
            />
            <StatCell
              label={language === "he" ? "שווי" : "Value"}
              value={formatILS(position.currentILS)}
              sub={`${position.shares.toLocaleString()} ${language === "he" ? "מניות" : "shares"}`}
            />
          </div>
        </>
      )}

      {/* ─── Your thesis ─── */}
      {ticker && (
        <>
          <Divider />
          <ThesisSection
            ticker={ticker}
            guidance={guidanceMap[ticker]}
            onUpdate={updateGuidance}
          />
        </>
      )}
    </div>
  );
}

function Divider() {
  return <div style={{ height: 1, background: "var(--bg-border)" }} />;
}

function SectionHeader({ label, meta }: { label: string; meta?: string }) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "baseline",
        justifyContent: "space-between",
        padding: "16px 16px 8px",
      }}
    >
      <span
        style={{
          fontSize: "var(--text-2xs)",
          textTransform: "uppercase",
          letterSpacing: "0.06em",
          color: "var(--text-tertiary)",
          fontWeight: "var(--weight-regular)",
        }}
      >
        {label}
      </span>
      {meta && (
        <span
          style={{
            fontSize: "var(--text-2xs)",
            color: "var(--text-tertiary)",
            fontVariantNumeric: "tabular-nums",
          }}
        >
          {meta}
        </span>
      )}
    </div>
  );
}

function BullBearCard({
  kind,
  label,
  text,
}: {
  kind: "bull" | "bear";
  label: string;
  text: string | null | undefined;
}) {
  const bg = kind === "bull" ? "rgba(66,201,122,0.10)" : "rgba(226,80,80,0.10)";
  const border = kind === "bull" ? "var(--color-green-border)" : "var(--color-red-border)";
  const labelColor = kind === "bull" ? "var(--color-green)" : "var(--color-red)";

  return (
    <div
      style={{
        background: bg,
        borderRadius: "var(--radius-md)",
        border: `0.5px solid ${border}`,
        padding: "10px 12px",
      }}
    >
      <div
        style={{
          fontSize: "var(--text-2xs)",
          fontWeight: "var(--weight-bold)",
          color: labelColor,
          textTransform: "uppercase",
          letterSpacing: "0.06em",
          marginBottom: 4,
        }}
      >
        {label}
      </div>
      <div
        style={{
          fontSize: "var(--text-sm)",
          color: "var(--text-secondary)",
          lineHeight: 1.45,
        }}
      >
        {text ?? "—"}
      </div>
    </div>
  );
}

function ConditionRow({
  kind,
  text,
  label,
  verdict,
}: {
  kind: "entry" | "exit";
  text: string;
  label: string;
  verdict?: Verdict;
}) {
  let Icon: typeof Circle | typeof Check | typeof AlertTriangle = Circle;
  let dotColor = kind === "exit" ? "var(--color-amber)" : "var(--text-ghost)";

  if (verdict) {
    if (kind === "entry") {
      if (verdict === "BUY" || verdict === "ADD") {
        Icon = Check;
        dotColor = "var(--color-green)";
      } else if (verdict === "REDUCE" || verdict === "SELL" || verdict === "CLOSE") {
        Icon = AlertTriangle;
        dotColor = "var(--color-amber)";
      }
    } else {
      if (verdict === "SELL" || verdict === "CLOSE") {
        Icon = AlertTriangle;
        dotColor = "var(--color-red)";
      } else if (verdict === "REDUCE") {
        Icon = AlertTriangle;
        dotColor = "var(--color-amber)";
      }
    }
  }

  return (
    <div
      style={{
        display: "flex",
        alignItems: "flex-start",
        gap: 10,
        padding: "8px 0",
        borderTop: "0.5px solid var(--bg-border)",
      }}
    >
      <Icon
        size={10}
        color={dotColor}
        style={{ marginTop: 4, flexShrink: 0 }}
      />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: "var(--text-sm)", color: "var(--text-primary)", lineHeight: 1.4 }}>
          {text}
        </div>
      </div>
      <span
        style={{
          fontSize: "var(--text-2xs)",
          fontWeight: "var(--weight-bold)",
          color: kind === "entry" ? "var(--color-green)" : "var(--color-amber)",
          textTransform: "uppercase",
          letterSpacing: "0.06em",
          flexShrink: 0,
          marginTop: 2,
        }}
      >
        {label}
      </span>
    </div>
  );
}

function twoSentences(text: string | null | undefined): string {
  return reasoningSnippet(text, 280);
}

