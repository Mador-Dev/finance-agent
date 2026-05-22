import { getApplicationDataSource, isApplicationDatabaseConfigured } from "../db/applicationDataSource.js";

function requireDatabase(): void {
  if (!isApplicationDatabaseConfigured()) {
    throw new Error("APP_DATABASE_URL is required for orchestration state");
  }
}

export async function readOrchestrationState(
  userId: string,
  stateKey: string
): Promise<unknown | null> {
  requireDatabase();
  const ds = await getApplicationDataSource();
  const rows = (await ds.query(
    `SELECT payload FROM orchestration_state
     WHERE user_id = $1 AND state_key = $2 LIMIT 1`,
    [userId, stateKey]
  )) as Array<{ payload: unknown }>;
  return rows[0]?.payload ?? null;
}

export async function writeOrchestrationState(
  userId: string,
  stateKey: string,
  payload: unknown
): Promise<void> {
  requireDatabase();
  const ds = await getApplicationDataSource();
  await ds.query(
    `INSERT INTO orchestration_state (user_id, state_key, payload, updated_at)
     VALUES ($1, $2, $3::jsonb, NOW())
     ON CONFLICT (user_id, state_key) DO UPDATE SET
       payload = EXCLUDED.payload,
       updated_at = NOW()`,
    [userId, stateKey, JSON.stringify(payload)]
  );
}
