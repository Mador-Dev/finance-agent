import { NotificationPreferencesSchema, type NotificationPreferences } from "../schemas/notifications.js";
import { logger } from "./logger.js";
import { getApplicationDataSource, isApplicationDatabaseConfigured } from "../db/applicationDataSource.js";
import {
  composeNotification,
  renderTelegramNotification,
  renderWebNotification,
  type ComposedNotification,
  type SemanticNotificationRequest,
} from "./notificationComposer.js";
import {
  insertNotification as dbInsertNotification,
  updateDelivery as dbUpdateDelivery,
  listNotifications as dbListNotifications,
  markRead as dbMarkRead,
  listByBatch as dbListByBatch,
} from "./notificationStore.js";
import { sendTelegramMessage } from "./telegramDelivery.js";


const DEFAULT_NOTIFICATION_PREFERENCES: NotificationPreferences = NotificationPreferencesSchema.parse({
  primaryChannel: "telegram",
  enabledChannels: {
    telegram: true,
    web: true,
    whatsapp: false,
  },
  categories: {
    dailyBriefs: true,
    reportRuns: true,
    marketNews: true,
  },
});

async function isTelegramConnected(userId: string): Promise<boolean> {
  if (!isApplicationDatabaseConfigured()) return false;
  try {
    const ds = await getApplicationDataSource();
    const rows = await ds.query(
      `SELECT 1 FROM users WHERE user_id = $1 AND telegram_chat_id IS NOT NULL AND telegram_bot_token IS NOT NULL LIMIT 1`,
      [userId]
    ) as unknown[];
    return rows.length > 0;
  } catch {
    return false;
  }
}

export async function getNotificationPreferences(
  userId: string
): Promise<NotificationPreferences> {
  const telegramConnected = await isTelegramConnected(userId);
  let base = DEFAULT_NOTIFICATION_PREFERENCES;
  if (isApplicationDatabaseConfigured()) {
    try {
      const ds = await getApplicationDataSource();
      const rows = (await ds.query(
        `SELECT notification_preferences FROM users WHERE user_id = $1`,
        [userId]
      )) as Array<{ notification_preferences: unknown }>;
      const prefs = rows[0]?.notification_preferences;
      if (prefs && typeof prefs === "object" && Object.keys(prefs as object).length > 0) {
        const result = NotificationPreferencesSchema.safeParse(prefs);
        if (result.success) base = result.data;
      }
    } catch {}
  }
  return {
    ...base,
    primaryChannel: base.primaryChannel === "telegram" && !telegramConnected ? "web" : base.primaryChannel,
    enabledChannels: {
      ...base.enabledChannels,
      telegram: base.enabledChannels.telegram && telegramConnected,
      whatsapp: false,
    },
  };
}

export async function setNotificationPreferences(
  userId: string,
  preferences: NotificationPreferences
): Promise<NotificationPreferences> {
  const validated = NotificationPreferencesSchema.parse(preferences);
  const telegramConnected = await isTelegramConnected(userId);
  const normalized = {
    ...validated,
    primaryChannel: validated.primaryChannel === "telegram" && !telegramConnected ? "web" : validated.primaryChannel,
    enabledChannels: {
      ...validated.enabledChannels,
      telegram: validated.enabledChannels.telegram && telegramConnected,
      whatsapp: false,
    },
  } satisfies NotificationPreferences;

  if (isApplicationDatabaseConfigured()) {
    const ds = await getApplicationDataSource();
    await ds.query(
      `UPDATE users SET notification_preferences = $1::jsonb WHERE user_id = $2`,
      [JSON.stringify(normalized), userId]
    );
  }
  return normalized;
}

export interface NotificationEnvelope {
  id: string;
  userId: string;
  category: "daily_brief" | "report" | "market_news";
  title: string;
  body: string;
  ticker: string | null;
  batchId: string | null;
  channel: "telegram" | "web" | "whatsapp";
  createdAt: string;
  delivered: boolean;
  deliveredAt: string | null;
  readAt: string | null;
  error: string | null;
}

export interface NotificationPublishRequest extends SemanticNotificationRequest {
  userId: string;
}

function categoryEnabled(preferences: NotificationPreferences, category: NotificationEnvelope["category"]): boolean {
  if (category === "daily_brief") return preferences.categories.dailyBriefs;
  if (category === "report") return preferences.categories.reportRuns;
  return preferences.categories.marketNews;
}

function logNotificationEvent(
  level: "info" | "warn",
  fields: Record<string, string | number | boolean | null | string[]>
): void {
  logger[level](JSON.stringify({ event: "notification_publication", ...fields }));
}

function renderRecordContent(
  composed: ComposedNotification,
  channel: NotificationEnvelope["channel"]
): Pick<NotificationEnvelope, "category" | "title" | "body" | "ticker" | "batchId"> {
  if (channel === "telegram") {
    const telegram = renderTelegramNotification(composed);
    return {
      category: composed.category,
      title: composed.title,
      body: telegram.text,
      ticker: composed.ticker,
      batchId: composed.batchId,
    };
  }

  const web = renderWebNotification(composed);
  return {
    category: web.category,
    title: web.title,
    body: web.body,
    ticker: web.ticker,
    batchId: web.batchId,
  };
}

async function getTelegramTarget(userId: string): Promise<{ botToken: string; chatId: string } | null> {
  if (!isApplicationDatabaseConfigured()) return null;
  try {
    const ds = await getApplicationDataSource();
    const rows = await ds.query(
      `SELECT telegram_chat_id, telegram_bot_token FROM users WHERE user_id = $1 LIMIT 1`,
      [userId]
    ) as Array<{ telegram_chat_id: string | null; telegram_bot_token: string | null }>;
    const row = rows[0];
    if (!row?.telegram_chat_id || !row?.telegram_bot_token) return null;
    return { botToken: row.telegram_bot_token, chatId: row.telegram_chat_id };
  } catch {
    return null;
  }
}

async function deliverTelegram(record: NotificationEnvelope): Promise<{ delivered: boolean; error: string | null; attemptedChunks: number }> {
  const target = await getTelegramTarget(record.userId);
  if (!target) {
    return { delivered: false, error: "telegram target not configured", attemptedChunks: 0 };
  }

  const result = await sendTelegramMessage({
    botToken: target.botToken,
    chatId: target.chatId,
    text: record.body,
  });

  return {
    delivered: result.delivered,
    error: result.error,
    attemptedChunks: result.attemptedChunks,
  };
}


function buildCandidateChannels(
  preferences: NotificationPreferences,
  telegramConnected: boolean
): Array<NotificationEnvelope["channel"]> {
  const channels: Array<NotificationEnvelope["channel"]> = [];
  if (preferences.enabledChannels.web) channels.push("web");
  if (preferences.enabledChannels.telegram && telegramConnected) channels.push("telegram");
  if (preferences.primaryChannel !== "none") {
    channels.sort((a, b) =>
      a === preferences.primaryChannel ? -1 : b === preferences.primaryChannel ? 1 : 0
    );
  }
  return channels;
}

export async function publishNotification(
  request: NotificationPublishRequest
): Promise<NotificationEnvelope[]> {
  const composed = composeNotification(request);
  const preferences = await getNotificationPreferences(request.userId);
  if (!categoryEnabled(preferences, composed.category)) {
    logNotificationEvent("info", {
      decision: "category_disabled",
      userId: request.userId,
      semanticKind: composed.kind,
      category: composed.category,
      batchId: composed.batchId,
      channels: [],
    });
    return [];
  }

  if (composed.batchId) {
    const existing = await dbListByBatch(request.userId, composed.batchId, composed.category);
    if (existing.length > 0) {
      logNotificationEvent("info", {
        decision: "duplicate_batch",
        userId: request.userId,
        semanticKind: composed.kind,
        category: composed.category,
        batchId: composed.batchId,
        channels: existing.map((item) => item.channel),
      });
      return existing as NotificationEnvelope[];
    }
  }

  const telegramConnected = await isTelegramConnected(request.userId);
  const candidateChannels = buildCandidateChannels(preferences, telegramConnected);

  const createdAt = new Date().toISOString();
  const records: NotificationEnvelope[] = candidateChannels.map((channel) => ({
    id: `ntf_${Date.now()}_${channel}_${Math.random().toString(16).slice(2, 8)}`,
    userId: request.userId,
    createdAt,
    delivered: channel === "web",
    deliveredAt: channel === "web" ? createdAt : null,
    readAt: null,
    error: channel === "web" ? null : "pending delivery",
    channel,
    ...renderRecordContent(composed, channel),
  }));

  const deliveryOutcomes: string[] = [];

  for (const record of records) {
    await dbInsertNotification({
      id: record.id,
      userId: record.userId,
      category: record.category,
      channel: record.channel,
      title: record.title,
      body: record.body,
      ticker: record.ticker,
      batchId: record.batchId,
      delivered: record.delivered,
      deliveredAt: record.deliveredAt,
      readAt: record.readAt,
      error: record.error,
    });

    if (record.channel === "telegram") {
      const result = await deliverTelegram(record);
      const deliveredAtIso = result.delivered ? new Date().toISOString() : null;
      deliveryOutcomes.push(`telegram:${result.delivered ? "delivered" : "failed"}:${result.attemptedChunks}`);
      await dbUpdateDelivery(record.userId, record.id, {
        delivered: result.delivered,
        deliveredAt: deliveredAtIso,
        error: result.error,
      });
      record.delivered = result.delivered;
      record.deliveredAt = deliveredAtIso;
      record.error = result.error;
    }
  }

  logNotificationEvent("info", {
    decision: records.length > 0 ? "published" : "no_channels",
    userId: request.userId,
    semanticKind: composed.kind,
    category: composed.category,
    batchId: composed.batchId,
    channels: candidateChannels,
    deliveryOutcome: deliveryOutcomes.join(",") || (records.length > 0 ? "web:delivered" : "none"),
  });
  return records;
}

export async function listNotifications(
  userId: string,
  options?: { limit?: number; channel?: NotificationEnvelope["channel"] | null; unreadOnly?: boolean }
): Promise<NotificationEnvelope[]> {
  return dbListNotifications(userId, options) as Promise<NotificationEnvelope[]>;
}

export async function markNotificationsRead(userId: string, ids: string[]): Promise<number> {
  return dbMarkRead(userId, ids);
}

export { DEFAULT_NOTIFICATION_PREFERENCES };
