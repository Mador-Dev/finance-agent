import { getApplicationDataSource, isApplicationDatabaseConfigured } from "../db/applicationDataSource.js";
import {
  SystemControlSchema,
  UserControlSchema,
  type SystemControl,
  type UserControl,
} from "../schemas/control.js";
import { logger } from "./logger.js";

function requireDatabase(): void {
  if (!isApplicationDatabaseConfigured()) {
    throw new Error("APP_DATABASE_URL is required for control state");
  }
}

function applyUserControlExpiry(control: UserControl): UserControl {
  if (control.restriction && control.restrictedUntil) {
    if (new Date(control.restrictedUntil) < new Date()) {
      return { ...control, restriction: null, restrictedAt: null, restrictedUntil: null };
    }
  }
  return control;
}

function applySystemControlExpiry(control: SystemControl): SystemControl {
  if (control.locked && control.lockedUntil) {
    if (new Date(control.lockedUntil) < new Date()) {
      return { ...control, locked: false, lockedAt: null, lockedUntil: null };
    }
  }
  return control;
}

export async function getUserControl(userId: string): Promise<UserControl> {
  requireDatabase();
  const ds = await getApplicationDataSource();
  const rows = (await ds.query(
    `SELECT body FROM user_control WHERE user_id = $1 LIMIT 1`,
    [userId]
  )) as Array<{ body: unknown }>;

  const parsed = UserControlSchema.parse(rows[0]?.body ?? {});
  const control = applyUserControlExpiry(parsed);
  if (control !== parsed) {
    await setUserControl(userId, control);
  }
  return control;
}

export async function setUserControl(userId: string, control: Partial<UserControl>): Promise<void> {
  requireDatabase();
  const current = await getUserControl(userId);
  const merged = UserControlSchema.parse({ ...current, ...control });
  const ds = await getApplicationDataSource();
  await ds.query(
    `INSERT INTO user_control (user_id, body, updated_at)
     VALUES ($1, $2::jsonb, NOW())
     ON CONFLICT (user_id) DO UPDATE SET
       body = EXCLUDED.body,
       updated_at = NOW()`,
    [userId, JSON.stringify(merged)]
  );
  logger.info(`Set control for ${userId}: restriction=${merged.restriction ?? "none"}`);
}

export async function clearUserControl(userId: string): Promise<void> {
  await setUserControl(userId, {
    restriction: null,
    reason: "",
    restrictedAt: null,
    restrictedUntil: null,
    banner: null,
  });
}

export async function getSystemControl(): Promise<SystemControl> {
  requireDatabase();
  const ds = await getApplicationDataSource();
  const rows = (await ds.query(`SELECT body FROM system_control WHERE id = 1 LIMIT 1`)) as Array<{
    body: unknown;
  }>;
  const parsed = SystemControlSchema.parse(rows[0]?.body ?? {});
  const control = applySystemControlExpiry(parsed);
  if (control !== parsed) {
    await setSystemControl(control);
  }
  return control;
}

export async function setSystemControl(control: Partial<SystemControl>): Promise<void> {
  requireDatabase();
  const current = await getSystemControl();
  const merged = SystemControlSchema.parse({ ...current, ...control });
  const ds = await getApplicationDataSource();
  await ds.query(
    `INSERT INTO system_control (id, body, updated_at)
     VALUES (1, $1::jsonb, NOW())
     ON CONFLICT (id) DO UPDATE SET
       body = EXCLUDED.body,
       updated_at = NOW()`,
    [JSON.stringify(merged)]
  );
  logger.info(`System control updated: locked=${merged.locked}`);
}
