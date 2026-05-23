import { useQuery } from "@tanstack/react-query";
import { useLocation } from "react-router-dom";
import { fetchBalance } from "../../api/balance";

/**
 * Global points badge — shown in the top-right of every protected page.
 * When exhausted, shows time until the 24h window resets.
 */

function timeUntilReset(windowEnd: string): string {
  const ms = new Date(windowEnd).getTime() - Date.now();
  if (ms <= 0) return "soon";
  const h = Math.floor(ms / 3_600_000);
  const m = Math.floor((ms % 3_600_000) / 60_000);
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
}

export function PointsBadge() {
  const location = useLocation();
  const { data: balance } = useQuery({
    queryKey: ["balance"],
    queryFn: fetchBalance,
    staleTime: 30_000,
    refetchInterval: 60_000,
    retry: 1,
  });

  if (!balance || location.pathname === "/chat") return null;

  const label = balance.exhausted
    ? `Resets in ${timeUntilReset(balance.windowEnd)}`
    : balance.pointsRemaining >= 1000
    ? `${(balance.pointsRemaining / 1000).toFixed(1)}k pts`
    : `${balance.pointsRemaining.toFixed(0)} pts`;

  return (
    <div
      style={{
        position: "fixed",
        top: "env(safe-area-inset-top, 0px)",
        right: 12,
        zIndex: 50,
        marginTop: 10,
        display: "inline-flex",
        alignItems: "center",
        gap: 6,
        padding: "7px 12px 6px",
        borderRadius: 999,
        border: `2px solid ${balance.exhausted ? "rgba(185,28,28,0.72)" : "rgba(22,101,52,0.72)"}`,
        background: balance.exhausted ? "#ffe5e5" : "#effed9",
        boxShadow: balance.exhausted ? "4px 4px 0 rgba(185,28,28,0.18)" : "4px 4px 0 rgba(22,101,52,0.18)",
        pointerEvents: "none",
      }}
    >
      <span
        aria-hidden="true"
        style={{
          width: 10,
          height: 10,
          borderRadius: "50%",
          background: balance.exhausted ? "#ef4444" : "#65a30d",
          border: "2px solid rgba(34,30,26,0.75)",
          flexShrink: 0,
        }}
      />
      <span
        style={{
          fontSize: 11,
          fontWeight: 800,
          color: balance.exhausted ? "#991b1b" : "#166534",
          letterSpacing: "0.01em",
        }}
      >
        {label}
      </span>
    </div>
  );
}
