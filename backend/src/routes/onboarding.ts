import { Router } from "express";
import type { Response, NextFunction } from "express";
import type { AuthenticatedRequest } from "../middleware/auth.js";
import type { UserWorkspace } from "../middleware/userIsolation.js";
import type { Profile } from "../schemas/onboarding.js";
import {
  OnboardInitSchema,
  ProfileSchema,
  NotificationPreferencesUpdateSchema,
  ScheduleSchema,
  PositionGuidanceCompletionSchema,
  type PositionGuidance,
} from "../schemas/onboarding.js";
import { TelegramConnectRequestSchema } from "../schemas/channels.js";
import { PortfolioFileSchema } from "../schemas/portfolio.js";
import { hashPassword, verifyPassword } from "../middleware/auth.js";
import { writeUserAuth } from "../services/userStore.js";
import { readPortfolio } from "../services/portfolioStore.js";
import {
  createUserWorkspace,
  ensureUserProvisioned,
  workspaceExists,
  saveUserPortfolio,
} from "../services/workspaceService.js";
import { authMiddleware } from "../middleware/auth.js";
import { ensureUserProvisionedMiddleware } from "../middleware/ensureUserProvisioned.js";
import { userIsolationMiddleware } from "../middleware/userIsolation.js";
import { getNotificationPreferences, setNotificationPreferences } from "../services/notificationService.js";
import { readState, writeState } from "../services/stateService.js";
import { getApplicationDataSource, isApplicationDatabaseConfigured } from "../db/applicationDataSource.js";

const router = Router();

const authGuard = [
  authMiddleware,
  ensureUserProvisionedMiddleware,
  userIsolationMiddleware,
] as const;

type AsyncHandler = (
  req: AuthenticatedRequest,
  res: Response,
  next: NextFunction
) => Promise<void>;

function handler(fn: AsyncHandler) {
  return (req: AuthenticatedRequest, res: Response, next: NextFunction) => {
    fn(req, res, next).catch(next);
  };
}

// ── POST /api/onboard/init ──────────────────────────────────────────────────

router.post(
  "/init",
  handler(async (req, res) => {
    // Admin key check
    const expectedKey = process.env["ADMIN_KEY"];
    const adminKey = req.headers["x-admin-key"];
    if (!expectedKey || adminKey !== expectedKey) {
      res.status(401).json({ error: "unauthorized" });
      return;
    }

    // Validate input
    const parsed = OnboardInitSchema.safeParse(req.body);
    if (!parsed.success) {
      res.status(400).json({
        error: "Validation failed",
        details: parsed.error.errors,
      });
      return;
    }

    const { userId, password, displayName, schedule } =
      parsed.data;

    // Check workspace doesn't exist
    if (await workspaceExists(userId)) {
      res.status(409).json({ error: "User already exists" });
      return;
    }

    // Create workspace
    await createUserWorkspace(userId);

    const { ensureUserRecord } = await import("../services/userStore.js");
    const userRecord: Record<string, unknown> = {
      displayName,
      schedule: schedule as Record<string, unknown>,
    };
    if (password) {
      const hash = await hashPassword(password);
      await writeUserAuth(userId, { passwordHash: hash, tokenVersion: 0 });
      userRecord.passwordHash = hash;
    }
    await ensureUserRecord(userId, userRecord);

    const { readPersonaMd, writePersonaMd } = await import("../services/personaStore.js");
    const userMdRaw = (await readPersonaMd(userId)) ?? "";
    await writePersonaMd(userId, userMdRaw.replace(/\[DISPLAY_NAME\]/g, displayName));

    res.status(201).json({
      userId,
      created: true,
      nextStep: "submit_portfolio",
    });
  })
);

// ── POST /api/onboard/provision ─────────────────────────────────────────────
// Clerk-authenticated users: create DB workspace without admin key.

router.post(
  "/provision",
  authMiddleware,
  ensureUserProvisionedMiddleware,
  handler(async (req: AuthenticatedRequest, res: Response) => {
    const userId = res.locals["userId"] as string;
    const displayName =
      typeof req.body?.displayName === "string" && req.body.displayName.trim().length > 0
        ? req.body.displayName.trim().slice(0, 64)
        : undefined;

    const result = await ensureUserProvisioned(userId, { displayName });
    res.status(result.created ? 201 : 200).json({
      userId,
      created: result.created,
      nextStep: "submit_portfolio",
    });
  })
);

// ── POST /api/onboard/portfolio ─────────────────────────────────────────────

router.post(
  "/portfolio",
  ...authGuard,
  handler(async (req: AuthenticatedRequest, res: Response) => {
    const ws = res.locals["workspace"] as UserWorkspace;

    // Extract optional schedule from body
    const { schedule: incomingSchedule, ...portfolioBody } = req.body as {
      schedule?: unknown;
      [key: string]: unknown;
    };

    // Validate portfolio
    const parsed = PortfolioFileSchema.safeParse(portfolioBody);
    if (!parsed.success) {
      res.status(400).json({
        error: "Validation failed",
        details: parsed.error.errors,
      });
      return;
    }

    const userId = ws.userId;

    // Idempotent: persist portfolio and open the optional position-guidance window.
    await saveUserPortfolio(userId, parsed.data);

    // Save schedule to profile.json if provided
    if (incomingSchedule) {
      try {
        const { updateUserSchedule } = await import("../services/userStore.js");
        await updateUserSchedule(ws.userId, incomingSchedule as Record<string, unknown>);
      } catch { /* non-fatal */ }
    }

    res.status(200).json({
      state: "INCOMPLETE",
      nextStep: "position_guidance",
      guidanceStepPending: true,
      message:
        "Portfolio saved. Add optional position guidance or skip to start analysis.",
    });
  })
);

router.get(
  "/position-guidance",
  ...authGuard,
  handler(async (_req: AuthenticatedRequest, res: Response) => {
    const ws = res.locals["workspace"] as UserWorkspace;
    const state = await readState(ws.userId);

    let tickers: string[] = [];
    const storedPortfolio = await readPortfolio(ws.userId).catch(() => null);
    if (storedPortfolio) {
      const portfolio = PortfolioFileSchema.parse(storedPortfolio);
      tickers = Array.from(
        new Set(Object.values(portfolio.accounts).flat().map((position) => position.ticker))
      ).sort();
    }

    res.json({
      status: state.onboarding.positionGuidanceStatus,
      tickers,
      guidance: state.onboarding.positionGuidance,
    });
  })
);

router.post(
  "/position-guidance/complete",
  ...authGuard,
  handler(async (req: AuthenticatedRequest, res: Response) => {
    const ws = res.locals["workspace"] as UserWorkspace;
    const parsed = PositionGuidanceCompletionSchema.safeParse(req.body);
    if (!parsed.success) {
      res.status(400).json({
        error: "Validation failed",
        details: parsed.error.errors,
      });
      return;
    }

    const storedPortfolio = await readPortfolio(ws.userId);
    if (!storedPortfolio) {
      res.status(404).json({ error: "portfolio not found" });
      return;
    }
    const portfolio = PortfolioFileSchema.parse(storedPortfolio);
    const validTickers = new Set(
      Object.values(portfolio.accounts).flat().map((position) => position.ticker)
    );
    const cleanedGuidance = Object.fromEntries(
      Object.entries(parsed.data.guidance).filter(([ticker, guidance]) => {
        if (!validTickers.has(ticker)) return false;
        return (
          guidance.thesis.length > 0 ||
          guidance.horizon !== "unspecified" ||
          guidance.addOn.length > 0 ||
          guidance.reduceOn.length > 0 ||
          guidance.notes.length > 0
        );
      })
    ) as Record<string, PositionGuidance>;

    const currentState = await readState(ws.userId);
    if (currentState.state === "BOOTSTRAPPING" || currentState.state === "ACTIVE") {
      res.json({
        state: currentState.state,
        guidanceStepPending: false,
        message: "Analysis has already started.",
      });
      return;
    }

    await writeState(ws.userId, {
      onboarding: {
        ...currentState.onboarding,
        positionGuidanceStatus: parsed.data.skip ? "skipped" : "completed",
        positionGuidance: cleanedGuidance,
      },
    });

    res.status(200).json({
      state: currentState.state,
      guidanceStepPending: false,
      message: "Guidance saved. Launch bootstrap on the agents service to begin analysis.",
    });
  })
);

// ── GET /api/onboard/status ─────────────────────────────────────────────────

router.get(
  "/status",
  ...authGuard,
  handler(async (_req: AuthenticatedRequest, res: Response) => {
    const ws = res.locals["workspace"] as UserWorkspace;
    const userId = ws.userId;

    let stateData: Awaited<ReturnType<typeof readState>>;
    try {
      stateData = await readState(userId);
    } catch {
      res.status(500).json({ error: "Cannot read state file" });
      return;
    }

    const { getUserOnboardingProfile } = await import("../services/userStore.js");
    const dbProfile = await getUserOnboardingProfile(userId).catch(() => null);
    let profile: Profile | null = null;
    if (dbProfile) {
      profile = ProfileSchema.parse({
        userId,
        displayName: dbProfile.displayName,
        telegramChatId: "",
        schedule: dbProfile.schedule,
        createdAt: new Date().toISOString(),
      });
    }

    let portfolioLoaded = false;
    const storedPortfolio = await readPortfolio(userId).catch(() => null);
    if (storedPortfolio) {
      portfolioLoaded = PortfolioFileSchema.safeParse(storedPortfolio).success;
    }

    const bp = stateData.bootstrapProgress;
    const bootstrapProgress =
      bp !== null
        ? {
            total: bp.total,
            completed: bp.completed,
            completedTickers: bp.completedTickers,
            pct:
              bp.total > 0
                ? Math.round((bp.completed / bp.total) * 100)
                : 0,
          }
        : null;

    let telegramChatId: string | null = null;
    let telegramConnected = false;
    if (isApplicationDatabaseConfigured()) {
      const ds = await getApplicationDataSource();
      const userRows = await ds.query(
        `SELECT telegram_chat_id, telegram_bot_token FROM users WHERE user_id = $1 LIMIT 1`,
        [userId]
      ) as Array<{ telegram_chat_id: string | null; telegram_bot_token: string | null }>;
      telegramChatId = userRows[0]?.telegram_chat_id ?? null;
      telegramConnected = !!telegramChatId && !!userRows[0]?.telegram_bot_token;
    }
    const notifications = await getNotificationPreferences(userId);

    res.json({
      userId,
      state: stateData.state,
      displayName: profile?.displayName ?? null,
      telegramChatId,
      bootstrapProgress,
      portfolioLoaded,
      guidanceStepPending: stateData.onboarding?.positionGuidanceStatus === "pending",
      positionGuidanceCount: Object.keys(stateData.onboarding?.positionGuidance ?? {}).length,
      readyForTrading: stateData.state === "ACTIVE",
      schedule: profile?.schedule ?? null,
      notifications,
      telegramConnected,
    });
  })
);

// POST /api/onboard/telegram
router.post(
  "/telegram",
  ...authGuard,
  handler(async (req: AuthenticatedRequest, res: Response) => {
    const ws = res.locals["workspace"] as UserWorkspace;
    const parsed = TelegramConnectRequestSchema.safeParse(req.body);
    if (!parsed.success) {
      res.status(400).json({ error: "Validation failed", details: parsed.error.errors });
      return;
    }
    if (isApplicationDatabaseConfigured()) {
      const ds = await getApplicationDataSource();
      await ds.query(
        `UPDATE users SET telegram_chat_id = $1, telegram_bot_token = $2 WHERE user_id = $3`,
        [parsed.data.telegramChatId, parsed.data.botToken, ws.userId]
      );
    }
    res.json({ connected: true, channel: "telegram" });
  })
);

// DELETE /api/onboard/telegram
router.delete(
  "/telegram",
  ...authGuard,
  handler(async (_req: AuthenticatedRequest, res: Response) => {
    const ws = res.locals["workspace"] as UserWorkspace;
    if (isApplicationDatabaseConfigured()) {
      const ds = await getApplicationDataSource();
      await ds.query(
        `UPDATE users SET telegram_chat_id = NULL, telegram_bot_token = NULL WHERE user_id = $1`,
        [ws.userId]
      );
    }
    res.json({ connected: false, channel: "telegram" });
  })
);

// POST /api/onboard/change-password
router.post(
  "/change-password",
  ...authGuard,
  handler(async (req: AuthenticatedRequest, res: Response) => {
    const ws = res.locals["workspace"] as UserWorkspace;
    const { currentPassword, newPassword } = req.body as {
      currentPassword?: string;
      newPassword?: string;
    };

    if (!currentPassword || !newPassword) {
      res.status(400).json({ error: "currentPassword and newPassword required" });
      return;
    }
    if (newPassword.length < 8) {
      res.status(400).json({ error: "newPassword must be at least 8 characters" });
      return;
    }

    const { readUserAuth } = await import("../services/userStore.js");
    const authData = await readUserAuth(ws.userId);
    if (!authData) {
      res.status(401).json({ error: "cannot read auth" });
      return;
    }

    const valid = await verifyPassword(currentPassword, authData.passwordHash);
    if (!valid) {
      res.status(401).json({ error: "incorrect_password" });
      return;
    }

    const hash = await hashPassword(newPassword);
    await writeUserAuth(ws.userId, { ...authData, passwordHash: hash });

    res.json({ changed: true });
  })
);

// PATCH /api/onboard/schedule
router.patch(
  "/schedule",
  ...authGuard,
  handler(async (req: AuthenticatedRequest, res: Response) => {
    const ws = res.locals["workspace"] as UserWorkspace;
    const parsed = ScheduleSchema.safeParse(req.body);
    if (!parsed.success) {
      res.status(400).json({ error: "Validation failed", details: parsed.error.errors });
      return;
    }

    const { updateUserSchedule } = await import("../services/userStore.js");
    await updateUserSchedule(ws.userId, parsed.data as Record<string, unknown>);

    res.json({ updated: true, schedule: parsed.data });
  })
);

router.patch(
  "/notifications",
  ...authGuard,
  handler(async (req: AuthenticatedRequest, res: Response) => {
    const ws = res.locals["workspace"] as UserWorkspace;
    const parsed = NotificationPreferencesUpdateSchema.safeParse(req.body);
    if (!parsed.success) {
      res.status(400).json({ error: "Validation failed", details: parsed.error.errors });
      return;
    }

    const notifications = await setNotificationPreferences(ws.userId, parsed.data);
    res.json({ updated: true, notifications });
  })
);

router.patch(
  "/display-name",
  ...authGuard,
  handler(async (req: AuthenticatedRequest, res: Response) => {
    const ws = res.locals["workspace"] as UserWorkspace;
    const { displayName } = req.body as { displayName?: string };
    if (!displayName || typeof displayName !== "string" || !displayName.trim()) {
      res.status(400).json({ error: "displayName is required" });
      return;
    }
    const trimmed = displayName.trim().slice(0, 64);
    const { updateUserDisplayName } = await import("../services/userStore.js");
    await updateUserDisplayName(ws.userId, trimmed);
    res.json({ updated: true, displayName: trimmed });
  })
);

export default router;
