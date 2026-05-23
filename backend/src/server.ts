import "dotenv/config";
import { createApp } from "./app.js";
import { logger } from "./services/logger.js";
import { startWatchdog } from "./services/scheduler/watchdog.js";
import { syncAllUserProfiles, syncSystemAgentProfile } from "./services/profileService.js";
import { repairActiveUserState } from "./services/stateService.js";
import { reconcileWorkspaceIntegrity } from "./services/workspaceService.js";
import { listUserIds } from "./services/userStore.js";
import { buildWorkspace } from "./middleware/userIsolation.js";
import { getApplicationDataSource, isApplicationDatabaseConfigured } from "./db/applicationDataSource.js";
import { runStartupGuards } from "./services/security/startupGuards.js";

const PORT = parseInt(process.env["PORT"] ?? "8081", 10);
const USERS_DIR = process.env["USERS_DIR"] ?? "../users";

const app = createApp();

async function reconcileStartupState(): Promise<void> {
  try {
    const userIds = await listUserIds();
    let workspaceRepairs = 0;
    for (const userId of userIds) {
      await repairActiveUserState(userId);
      buildWorkspace(userId, USERS_DIR);
      const result = await reconcileWorkspaceIntegrity(userId);
      if (result.changed) workspaceRepairs += 1;
    }
    logger.info(`Startup reconciliation complete: users=${userIds.length} workspaceRepairs=${workspaceRepairs}`);
  } catch (err) {
    logger.warn(`Startup reconciliation failed: ${err instanceof Error ? err.message : String(err)}`);
  }
}

async function bootstrap(): Promise<void> {
  const guard = await runStartupGuards();
  if (!guard.ok) {
    logger.error(`Startup guards failed: ${guard.failures.join(", ")}`);
    process.exit(78);
  }

  if (isApplicationDatabaseConfigured()) {
    try {
      await getApplicationDataSource();
      logger.info("Application database connected");
    } catch (err) {
      logger.warn(`Database connection failed: ${err instanceof Error ? err.message : String(err)}`);
    }
  }

  const server = app.listen(PORT, () => {
    logger.info(`Server started on port ${PORT}`);
    startWatchdog();
    setImmediate(() => {
      void syncAllUserProfiles();
      void syncSystemAgentProfile();
      void reconcileStartupState();
    });
  });

  server.on("error", (err: NodeJS.ErrnoException) => {
    logger.error(`Server failed to start: ${err.message}`);
    process.exit(1);
  });
}

void bootstrap().catch((err) => {
  logger.error(`Bootstrap failed: ${err instanceof Error ? err.message : String(err)}`);
  process.exit(1);
});
