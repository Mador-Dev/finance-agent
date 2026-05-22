import { getApplicationDataSource, isApplicationDatabaseConfigured } from "../db/applicationDataSource.js";
import type { SupportMessageCreate, SupportMessageRecord } from "../schemas/support.js";

function requireDatabase(): void {
  if (!isApplicationDatabaseConfigured()) {
    throw new Error("APP_DATABASE_URL is required for support messages");
  }
}

function rowToRecord(row: {
  id: string;
  user_id: string;
  subject: string;
  message: string;
  source: string;
  page: string | null;
  status: SupportMessageRecord["status"];
  created_at: Date | string;
}): SupportMessageRecord {
  const createdAt =
    row.created_at instanceof Date ? row.created_at.toISOString() : String(row.created_at);
  return {
    id: row.id,
    userId: row.user_id,
    subject: row.subject,
    message: row.message,
    source: row.source as SupportMessageRecord["source"],
    page: row.page ?? undefined,
    createdAt,
    status: row.status,
  };
}

export async function submitSupportMessage(
  userId: string,
  input: SupportMessageCreate
): Promise<SupportMessageRecord> {
  requireDatabase();
  const id = `support_${Date.now()}_${Math.random().toString(16).slice(2, 8)}`;
  const ds = await getApplicationDataSource();
  await ds.query(
    `INSERT INTO support_messages (id, user_id, subject, message, source, page, status)
     VALUES ($1, $2, $3, $4, $5, $6, 'open')`,
    [id, userId, input.subject, input.message, input.source, input.page ?? null]
  );
  const rows = (await ds.query(`SELECT * FROM support_messages WHERE id = $1`, [id])) as Array<{
    id: string;
    user_id: string;
    subject: string;
    message: string;
    source: string;
    page: string | null;
    status: SupportMessageRecord["status"];
    created_at: Date | string;
  }>;
  return rowToRecord(rows[0]!);
}

export async function listSupportMessages(limit = 100): Promise<SupportMessageRecord[]> {
  requireDatabase();
  const ds = await getApplicationDataSource();
  const rows = (await ds.query(
    `SELECT * FROM support_messages ORDER BY created_at DESC LIMIT $1`,
    [limit]
  )) as Array<{
    id: string;
    user_id: string;
    subject: string;
    message: string;
    source: string;
    page: string | null;
    status: SupportMessageRecord["status"];
    created_at: Date | string;
  }>;
  return rows.map(rowToRecord);
}

export async function updateSupportMessageStatus(
  messageId: string,
  status: SupportMessageRecord["status"]
): Promise<SupportMessageRecord | null> {
  requireDatabase();
  const ds = await getApplicationDataSource();
  const updated = (await ds.query(
    `UPDATE support_messages SET status = $2 WHERE id = $1 RETURNING *`,
    [messageId, status]
  )) as Array<{
    id: string;
    user_id: string;
    subject: string;
    message: string;
    source: string;
    page: string | null;
    status: SupportMessageRecord["status"];
    created_at: Date | string;
  }>;
  if (!updated[0]) return null;
  return rowToRecord(updated[0]);
}
