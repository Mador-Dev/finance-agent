import { StrategySchema } from "../schemas/strategy.js";
import { isApplicationDatabaseConfigured } from "../db/applicationDataSource.js";
import { readStrategy } from "./strategyStore.js";
import { renderStrategyJson } from "./strategyExportService.js";
import {
  loadStrategyFile,
  type StrategyFileLoadOptions,
  type StrategyFileLoadResult,
} from "./strategyFileService.js";
import { logger } from "./logger.js";

/**
 * Load a user's strategy — Postgres first, legacy JSON file fallback.
 */
export async function loadUserStrategy(
  userId: string,
  filePath: string,
  options?: StrategyFileLoadOptions
): Promise<StrategyFileLoadResult> {
  const tickerHint = options?.tickerHint?.trim().toUpperCase();

  if (isApplicationDatabaseConfigured() && tickerHint) {
    try {
      const record = await readStrategy(userId, tickerHint);
      if (record) {
        const parsed = StrategySchema.safeParse(renderStrategyJson(record));
        if (parsed.success) {
          return {
            valid: true,
            strategy: parsed.data,
            repaired: false,
            repairNotes: [],
            filePath,
            validatedAt: new Date().toISOString(),
          };
        }
        return {
          valid: false,
          errors: parsed.error.errors.map((e) => `${e.path.join(".")}: ${e.message}`),
          repaired: false,
          repairNotes: [],
          filePath,
          validatedAt: new Date().toISOString(),
        };
      }
    } catch (err) {
      logger.warn(
        `loadUserStrategy DB read failed for ${userId}/${tickerHint}: ${
          err instanceof Error ? err.message : String(err)
        }`
      );
    }
  }

  if (!isApplicationDatabaseConfigured()) {
    return loadStrategyFile(filePath, options);
  }

  return {
    valid: false,
    errors: [`Strategy not found in database: ${tickerHint ?? "unknown"}`],
    repaired: false,
    repairNotes: [],
    filePath,
    validatedAt: new Date().toISOString(),
  };
}
