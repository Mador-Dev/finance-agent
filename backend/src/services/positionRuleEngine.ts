import { getApplicationDataSource, isApplicationDatabaseConfigured } from "../db/applicationDataSource.js";
import { logger } from "./logger.js";

export interface RuleCheckInput {
  userId: string;
  ticker: string;
  /** Current position weight as a percentage (0–100). */
  positionWeightPct: number;
  /** Drawdown from cost basis as a percentage (0–100, positive = loss). */
  drawdownPct: number;
}

export interface RuleCheckResult {
  triggered: boolean;
  trigger: "max_position_size" | "stop_loss" | null;
  reason: string | null;
  jobId: string | null;
}

export async function evaluatePositionRules(
  input: RuleCheckInput
): Promise<RuleCheckResult> {
  if (!isApplicationDatabaseConfigured()) {
    return { triggered: false, trigger: null, reason: null, jobId: null };
  }

  const ds = await getApplicationDataSource();

  // Read user thresholds from the `users` table (M1.1, M1.2).
  const userRows = (await ds.query(
    `SELECT max_single_position_pct, stop_loss_threshold_pct
       FROM users WHERE user_id = $1 LIMIT 1`,
    [input.userId]
  )) as Array<{ max_single_position_pct: string; stop_loss_threshold_pct: string }>;

  const userRow = userRows[0];
  if (!userRow) return { triggered: false, trigger: null, reason: null, jobId: null };

  const maxPositionPct = Number(userRow.max_single_position_pct);
  const stopLossPct = Number(userRow.stop_loss_threshold_pct);

  let trigger: RuleCheckResult["trigger"] = null;
  let reason: string | null = null;

  if (input.positionWeightPct > maxPositionPct) {
    trigger = "max_position_size";
    reason = `Position weight ${input.positionWeightPct.toFixed(1)}% exceeds max ${maxPositionPct}%`;
  } else if (input.drawdownPct >= stopLossPct) {
    trigger = "stop_loss";
    reason = `Drawdown ${input.drawdownPct.toFixed(1)}% exceeds stop-loss threshold ${stopLossPct}%`;
  }

  if (!trigger) return { triggered: false, trigger: null, reason: null, jobId: null };

  logger.info(`Position rule triggered: user=${input.userId} ticker=${input.ticker} trigger=${trigger} reason=${reason}`);

  return { triggered: true, trigger, reason, jobId: null };
}
