import { getApplicationDataSource, isApplicationDatabaseConfigured } from "../db/applicationDataSource.js";
import { getAdminDefaults } from "./adminDefaultsService.js";

export interface UserPointsBalanceSnapshot {
  dailyBudgetPoints: number;
  pointsUsed: number;
  pointsRemaining: number;
  pctUsed: number;
  exhausted: boolean;
  windowStart: string;
  windowEnd: string;
}

function roundPoints(value: number): number {
  return Math.round(value * 1_000) / 1_000;
}

function clampMinZero(value: number): number {
  return value > 0 ? value : 0;
}

export async function getEffectiveDailyPointsBudget(userId: string): Promise<number> {
  const defaults = await getAdminDefaults();
  if (!isApplicationDatabaseConfigured()) {
    return defaults.pointsBudget.dailyBudgetPoints;
  }

  const ds = await getApplicationDataSource();
  const rows = await ds.query(
    `SELECT daily_points_budget FROM users WHERE user_id = $1 LIMIT 1`,
    [userId]
  ) as Array<{ daily_points_budget: string | number | null }>;

  const raw = Number(rows[0]?.daily_points_budget);
  if (Number.isFinite(raw) && raw > 0) {
    return roundPoints(raw);
  }
  return roundPoints(defaults.pointsBudget.dailyBudgetPoints);
}

export async function setUserDailyPointsBudget(userId: string, dailyBudgetPoints: number): Promise<number> {
  if (!Number.isFinite(dailyBudgetPoints) || dailyBudgetPoints <= 0) {
    throw new Error("dailyBudgetPoints must be greater than zero");
  }
  if (!isApplicationDatabaseConfigured()) {
    return roundPoints(dailyBudgetPoints);
  }

  const ds = await getApplicationDataSource();
  await ds.query(
    `UPDATE users SET daily_points_budget = $2, updated_at = NOW() WHERE user_id = $1`,
    [userId, roundPoints(dailyBudgetPoints)]
  );
  return getEffectiveDailyPointsBudget(userId);
}

export async function grantUserPointsCredit(
  userId: string,
  points: number,
  note: string | null,
  refId?: string | null
): Promise<void> {
  if (!Number.isFinite(points) || points <= 0) {
    throw new Error("points must be greater than zero");
  }
  if (!isApplicationDatabaseConfigured()) return;

  const ds = await getApplicationDataSource();
  await ds.query(
    `INSERT INTO user_points_ledger (
       user_id, points_delta, entry_type, source, action, ref_id, note, expires_at
     ) VALUES (
       $1, $2, 'credit', 'admin', 'grant_credit', $3, $4, NOW() + INTERVAL '24 hours'
     )`,
    [userId, roundPoints(points), refId ?? null, note?.slice(0, 1_000) ?? null]
  );
}

export async function getUserPointsBalance(userId: string): Promise<UserPointsBalanceSnapshot> {
  const now = new Date();
  const windowStart = new Date(now.getTime() - 24 * 60 * 60 * 1_000).toISOString();

  const budget = await getEffectiveDailyPointsBudget(userId);
  if (!isApplicationDatabaseConfigured()) {
    return {
      dailyBudgetPoints: budget,
      pointsUsed: 0,
      pointsRemaining: budget,
      pctUsed: 0,
      exhausted: false,
      windowStart,
      windowEnd: new Date(now.getTime() + 24 * 60 * 60 * 1_000).toISOString(),
    };
  }

  const ds = await getApplicationDataSource();
  const rows = await ds.query(
    `SELECT
       COALESCE(SUM(CASE WHEN points_delta < 0 THEN -points_delta ELSE 0 END), 0) AS points_used,
       COALESCE(SUM(CASE WHEN points_delta > 0 THEN points_delta ELSE 0 END), 0) AS points_credits,
       MIN(expires_at) AS next_expiry
     FROM user_points_ledger
     WHERE user_id = $1
       AND expires_at > NOW()`,
    [userId]
  ) as Array<{
    points_used: string | number;
    points_credits: string | number;
    next_expiry: Date | string | null;
  }>;

  const pointsUsed = roundPoints(Number(rows[0]?.points_used ?? 0));
  const pointsCredits = roundPoints(Number(rows[0]?.points_credits ?? 0));
  const effectiveBudget = roundPoints(budget + pointsCredits);
  const pointsRemaining = roundPoints(clampMinZero(effectiveBudget - pointsUsed));
  const exhausted = pointsRemaining <= 0;
  const pctUsed = Math.max(0, Math.min(999, Math.round(
    effectiveBudget > 0 ? (pointsUsed / effectiveBudget) * 100 : 0
  )));
  const nextExpiry = rows[0]?.next_expiry ? new Date(rows[0].next_expiry).toISOString() : null;

  return {
    dailyBudgetPoints: effectiveBudget,
    pointsUsed,
    pointsRemaining,
    pctUsed,
    exhausted,
    windowStart,
    windowEnd: nextExpiry ?? new Date(now.getTime() + 24 * 60 * 60 * 1_000).toISOString(),
  };
}
