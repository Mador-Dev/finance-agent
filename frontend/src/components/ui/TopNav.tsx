import { useUser } from "@clerk/react";
import { useQuery, useQueryClient, useIsFetching } from "@tanstack/react-query";
import { useLocation } from "react-router-dom";
import { RefreshCw } from "lucide-react";
import { fetchBalance } from "../../api/balance";

function timeUntilReset(windowEnd: string): string {
  const ms = new Date(windowEnd).getTime() - Date.now();
  if (ms <= 0) return "soon";
  const h = Math.floor(ms / 3_600_000);
  const m = Math.floor((ms % 3_600_000) / 60_000);
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
}

export function TopNav() {
  const { user } = useUser();
  const location = useLocation();
  const queryClient = useQueryClient();
  const isPortfolio = location.pathname === "/portfolio";
  const isFetchingPortfolio = useIsFetching({ queryKey: ["portfolio"] }) > 0;

  const { data: balance } = useQuery({
    queryKey: ["balance"],
    queryFn: fetchBalance,
    staleTime: 30_000,
    refetchInterval: 60_000,
    retry: 1,
  });

  const firstName = user?.firstName || user?.username || "there";
  const initial = firstName[0]?.toUpperCase() ?? "?";

  const handleRefresh = () => {
    queryClient.invalidateQueries({ queryKey: ["portfolio"] });
    queryClient.invalidateQueries({ queryKey: ["jobs"] });
    queryClient.invalidateQueries({ queryKey: ["verdicts"] });
  };

  const pointsLabel = balance
    ? balance.exhausted
      ? `Resets ${timeUntilReset(balance.windowEnd)}`
      : balance.pointsRemaining >= 1000
      ? `${(balance.pointsRemaining / 1000).toFixed(1)}k pts`
      : `${balance.pointsRemaining.toFixed(0)} pts`
    : null;

  const exhausted = balance?.exhausted ?? false;

  return (
    <header className="sticky top-0 z-40 w-full border-b border-[var(--color-border)] bg-[var(--color-bg-base)]/90 backdrop-blur-md">
      <div className="flex h-14 items-center justify-between gap-3 px-4">

        {/* Left: avatar + greeting */}
        <div className="flex min-w-0 items-center gap-2.5">
          <div
            className="shrink-0 flex items-center justify-center rounded-full text-[11px] font-bold"
            style={{
              width: 30,
              height: 30,
              background: "var(--color-bg-muted)",
              border: "1.5px solid var(--color-border)",
              color: "var(--text-primary)",
            }}
          >
            {initial}
          </div>
          <p className="truncate text-sm">
            <span className="text-[var(--text-tertiary)]">Hey </span>
            <span className="font-semibold text-[var(--text-primary)]">{firstName}</span>
          </p>
        </div>

        {/* Right: refresh (portfolio only) + points pill */}
        <div className="flex shrink-0 items-center gap-2">
          {isPortfolio && (
            <button
              type="button"
              onClick={handleRefresh}
              aria-label="Refresh portfolio"
              className="
                inline-flex items-center gap-1.5
                rounded-lg border border-[var(--color-border)]
                bg-[var(--color-bg-muted)] px-2.5 py-1.5
                text-[11px] font-medium text-[var(--text-secondary)]
                transition-colors duration-150
                hover:text-[var(--text-primary)] hover:border-[var(--bg-border-mid)]
                active:scale-95
              "
            >
              <RefreshCw size={12} className={isFetchingPortfolio ? "animate-spin" : ""} />
              <span className="hidden sm:inline">Refresh</span>
            </button>
          )}

          {pointsLabel && (
            <div
              className="inline-flex items-center gap-1.5 rounded-full border px-2.5 py-[5px] text-[11px] font-bold tracking-tight"
              style={{
                borderColor: exhausted ? "var(--color-red-border)" : "var(--color-green-border)",
                background: exhausted ? "var(--color-red-bg)" : "var(--color-green-bg)",
                color: exhausted ? "var(--color-red)" : "var(--color-green)",
              }}
            >
              <span
                className="h-1.5 w-1.5 shrink-0 rounded-full"
                style={{ background: exhausted ? "var(--color-red)" : "var(--color-green)" }}
              />
              {pointsLabel}
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
