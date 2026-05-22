import { getApplicationDataSource, isApplicationDatabaseConfigured } from "../db/applicationDataSource.js";
import type { Job, JobAction, JobSource, JobStatus } from "../types/index.js";
import type { JsonValue } from "../types/index.js";
import { readUserModelTier } from "./stepQueue/modelTier.js";
import { MODEL_TIERS, type ModelTier } from "./stepQueue/types.js";

const LEGACY_TICKER_META_KEY = "__legacyTicker";

interface JobRow {
  id: string;
  user_id: string;
  action: string;
  status: string;
  source: string;
  model_tier: string;
  budget_admitted_at: Date | string | null;
  triggered_at: Date | string;
  started_at: Date | string | null;
  completed_at: Date | string | null;
  pause_reason: string | null;
  failure_reason: string | null;
  result: JsonValue | null;
}

function toIso(value: Date | string | null | undefined): string | null {
  if (value === null || value === undefined) return null;
  const d = value instanceof Date ? value : new Date(value);
  return Number.isNaN(d.getTime()) ? null : d.toISOString();
}

function extractLegacyTicker(result: JsonValue | null): string | null {
  if (!result || typeof result !== "object" || Array.isArray(result)) return null;
  const ticker = result[LEGACY_TICKER_META_KEY];
  return typeof ticker === "string" ? ticker : null;
}

function stripLegacyTickerMeta(result: JsonValue | null): JsonValue {
  if (!result || typeof result !== "object" || Array.isArray(result)) return result;
  const { [LEGACY_TICKER_META_KEY]: _removed, ...rest } = result as Record<string, JsonValue>;
  return Object.keys(rest).length > 0 ? rest : null;
}

function attachLegacyTickerMeta(result: JsonValue, ticker: string | null): JsonValue {
  if (!ticker) return result;
  if (result && typeof result === "object" && !Array.isArray(result)) {
    return { ...result, [LEGACY_TICKER_META_KEY]: ticker };
  }
  return { [LEGACY_TICKER_META_KEY]: ticker, value: result };
}

function rowToJob(row: JobRow, ticker: string | null): Job {
  const fromMeta = extractLegacyTicker(row.result);
  return {
    id: row.id,
    action: row.action as JobAction,
    ticker: ticker ?? fromMeta,
    source: row.source as JobSource,
    budget_admitted_at: toIso(row.budget_admitted_at),
    status: row.status as JobStatus,
    triggered_at: toIso(row.triggered_at) ?? new Date().toISOString(),
    started_at: toIso(row.started_at),
    completed_at: toIso(row.completed_at),
    result: stripLegacyTickerMeta(row.result),
    error: row.failure_reason ?? row.pause_reason ?? null,
  };
}

async function resolveJobTicker(jobId: string): Promise<string | null> {
  const ds = await getApplicationDataSource();
  const rows = (await ds.query(
    `SELECT ticker FROM ticker_work_items WHERE job_id = $1 ORDER BY position ASC LIMIT 1`,
    [jobId]
  )) as Array<{ ticker: string }>;
  return rows[0]?.ticker ?? null;
}

async function resolveModelTier(userId: string): Promise<ModelTier> {
  const tier = await readUserModelTier(userId);
  return (MODEL_TIERS as readonly string[]).includes(tier) ? tier : "balanced";
}

export async function createJobInDb(
  userId: string,
  job: Job
): Promise<void> {
  const ds = await getApplicationDataSource();
  const modelTier = await resolveModelTier(userId);
  const resultPayload = attachLegacyTickerMeta(job.result, job.ticker);
  await ds.query(
    `INSERT INTO jobs
       (id, user_id, action, status, source, model_tier, notify_per_ticker,
        budget_admitted_at, triggered_at, started_at, completed_at, failure_reason, result)
     VALUES ($1,$2,$3,$4,$5,$6,false,$7,$8,$9,$10,$11,$12)`,
    [
      job.id,
      userId,
      job.action,
      job.status,
      job.source ?? "backend_job",
      modelTier,
      job.budget_admitted_at ? new Date(job.budget_admitted_at) : null,
      new Date(job.triggered_at),
      job.started_at ? new Date(job.started_at) : null,
      job.completed_at ? new Date(job.completed_at) : null,
      job.error,
      resultPayload,
    ]
  );
}

export async function getJobFromDb(userId: string, jobId: string): Promise<Job | null> {
  const ds = await getApplicationDataSource();
  const rows = (await ds.query(
    `SELECT id, user_id, action, status, source, model_tier, budget_admitted_at,
            triggered_at, started_at, completed_at, pause_reason, failure_reason, result
     FROM jobs WHERE id = $1 AND user_id = $2 LIMIT 1`,
    [jobId, userId]
  )) as JobRow[];
  if (!rows[0]) return null;
  const ticker = await resolveJobTicker(jobId);
  return rowToJob(rows[0], ticker);
}

export async function listJobsFromDb(userId: string, limit: number): Promise<Job[]> {
  const ds = await getApplicationDataSource();
  const rows = (await ds.query(
    `SELECT id, user_id, action, status, source, model_tier, budget_admitted_at,
            triggered_at, started_at, completed_at, pause_reason, failure_reason, result
     FROM jobs WHERE user_id = $1
     ORDER BY triggered_at DESC
     LIMIT $2`,
    [userId, limit]
  )) as JobRow[];

  const jobs: Job[] = [];
  for (const row of rows) {
    const ticker = await resolveJobTicker(row.id);
    jobs.push(rowToJob(row, ticker));
  }
  return jobs;
}

export async function updateJobInDb(
  userId: string,
  jobId: string,
  update: Partial<Pick<Job, "status" | "started_at" | "completed_at" | "result" | "error" | "budget_admitted_at">>
): Promise<Job | null> {
  const current = await getJobFromDb(userId, jobId);
  if (!current) return null;

  const merged: Job = { ...current, ...update };
  const ds = await getApplicationDataSource();
  const resultPayload = attachLegacyTickerMeta(merged.result, merged.ticker);
  await ds.query(
    `UPDATE jobs SET
       status = $3,
       started_at = $4,
       completed_at = $5,
       failure_reason = $6,
       budget_admitted_at = $7,
       result = $8
     WHERE id = $1 AND user_id = $2`,
    [
      jobId,
      userId,
      merged.status,
      merged.started_at ? new Date(merged.started_at) : null,
      merged.completed_at ? new Date(merged.completed_at) : null,
      merged.error,
      merged.budget_admitted_at ? new Date(merged.budget_admitted_at) : null,
      resultPayload,
    ]
  );
  return getJobFromDb(userId, jobId);
}

export async function listRecentJobsForRateLimit(
  userId: string,
  action: JobAction,
  sinceIso: string
): Promise<Array<{ action: string; status: string; triggered_at: string; ticker: string | null }>> {
  if (!isApplicationDatabaseConfigured()) return [];
  const ds = await getApplicationDataSource();
  const rows = (await ds.query(
    `SELECT id, action, status, triggered_at, result
     FROM jobs
     WHERE user_id = $1 AND action = $2 AND triggered_at >= $3
       AND status NOT IN ('failed', 'cancelled', 'superseded')`,
    [userId, action, sinceIso]
  )) as Array<{
    id: string;
    action: string;
    status: string;
    triggered_at: Date | string;
    result: JsonValue | null;
  }>;

  const jobs: Array<{ action: string; status: string; triggered_at: string; ticker: string | null }> = [];
  for (const row of rows) {
    const ticker =
      extractLegacyTicker(row.result) ?? (await resolveJobTicker(row.id));
    jobs.push({
      action: row.action,
      status: row.status,
      triggered_at: toIso(row.triggered_at) ?? sinceIso,
      ticker,
    });
  }
  return jobs;
}

export function isJobStoreAvailable(): boolean {
  return isApplicationDatabaseConfigured();
}
