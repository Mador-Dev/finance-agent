import { getApplicationDataSource, isApplicationDatabaseConfigured } from "../db/applicationDataSource.js";

function requireDatabase(): void {
  if (!isApplicationDatabaseConfigured()) {
    throw new Error("APP_DATABASE_URL is required for report artifacts");
  }
}

export async function readReportArtifact(
  userId: string,
  ticker: string,
  artifactKey: string
): Promise<unknown | null> {
  requireDatabase();
  const ds = await getApplicationDataSource();
  const rows = (await ds.query(
    `SELECT payload FROM report_artifacts
     WHERE user_id = $1 AND ticker = $2 AND artifact_key = $3 LIMIT 1`,
    [userId, ticker.toUpperCase(), artifactKey]
  )) as Array<{ payload: unknown }>;
  return rows[0]?.payload ?? null;
}

export async function writeReportArtifact(
  userId: string,
  ticker: string,
  artifactKey: string,
  payload: unknown
): Promise<void> {
  requireDatabase();
  const ds = await getApplicationDataSource();
  await ds.query(
    `INSERT INTO report_artifacts (user_id, ticker, artifact_key, payload, updated_at)
     VALUES ($1, $2, $3, $4::jsonb, NOW())
     ON CONFLICT (user_id, ticker, artifact_key) DO UPDATE SET
       payload = EXCLUDED.payload,
       updated_at = NOW()`,
    [userId, ticker.toUpperCase(), artifactKey, JSON.stringify(payload)]
  );
}

export async function listReportArtifactTickers(userId: string): Promise<string[]> {
  requireDatabase();
  const ds = await getApplicationDataSource();
  const rows = (await ds.query(
    `SELECT DISTINCT ticker FROM report_artifacts WHERE user_id = $1 AND ticker <> '_global'`,
    [userId]
  )) as Array<{ ticker: string }>;
  return rows.map((r) => r.ticker);
}
