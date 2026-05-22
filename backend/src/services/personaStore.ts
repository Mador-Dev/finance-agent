import { getApplicationDataSource, isApplicationDatabaseConfigured } from "../db/applicationDataSource.js";
import { ensureUserRecord } from "./userStore.js";

function requireDatabase(): void {
  if (!isApplicationDatabaseConfigured()) {
    throw new Error("APP_DATABASE_URL is required for user persona");
  }
}

export async function readPersonaMd(userId: string): Promise<string | null> {
  requireDatabase();
  const ds = await getApplicationDataSource();
  const rows = (await ds.query(
    `SELECT persona_md FROM users WHERE user_id = $1 LIMIT 1`,
    [userId]
  )) as Array<{ persona_md: string | null }>;
  const text = rows[0]?.persona_md;
  return text && text.trim().length > 0 ? text : null;
}

export async function writePersonaMd(userId: string, personaMd: string): Promise<void> {
  requireDatabase();
  await ensureUserRecord(userId);
  const ds = await getApplicationDataSource();
  await ds.query(
    `UPDATE users SET persona_md = $2, updated_at = NOW() WHERE user_id = $1`,
    [userId, personaMd]
  );
}
