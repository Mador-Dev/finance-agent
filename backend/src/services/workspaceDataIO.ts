import path from "path";
import { isApplicationDatabaseConfigured } from "../db/applicationDataSource.js";
import { readPersonaMd, writePersonaMd } from "./personaStore.js";
import { readReportArtifact, writeReportArtifact } from "./reportArtifactStore.js";
import { readPortfolio, writePortfolio } from "./portfolioStore.js";
import { readStrategy, writeStrategy } from "./strategyStore.js";
import { renderStrategyJson } from "./strategyExportService.js";
import { strategyToWriteInput } from "./strategyExportService.js";
import { StrategySchema } from "../schemas/strategy.js";

const GLOBAL_TICKER = "_global";

export type ParsedWorkspacePath =
  | { kind: "report"; ticker: string; key: string }
  | { kind: "strategy"; ticker: string }
  | { kind: "persona" }
  | { kind: "portfolio" };

export function parseWorkspaceDataPath(
  userId: string,
  filePath: string
): ParsedWorkspacePath | null {
  const normalized = path.normalize(filePath).replace(/\\/g, "/");
  const marker = `/users/${userId}/`;
  const idx = normalized.indexOf(marker);
  const relative =
    idx >= 0 ? normalized.slice(idx + marker.length) : normalized.includes(`/${userId}/`)
      ? normalized.split(`/${userId}/`).pop() ?? ""
      : null;
  if (!relative) return null;

  if (relative === "USER.md") return { kind: "persona" };
  if (relative === "data/portfolio.json") return { kind: "portfolio" };

  const reportMatch = relative.match(/^data\/reports\/([^/]+)\/([^/]+)\.json$/);
  if (reportMatch) {
    return { kind: "report", ticker: reportMatch[1]!.toUpperCase(), key: reportMatch[2]!.replace(/\.json$/, "") };
  }

  const strategyMatch = relative.match(/^data\/tickers\/([^/]+)\/strategy\.json$/);
  if (strategyMatch) {
    return { kind: "strategy", ticker: strategyMatch[1]!.toUpperCase() };
  }

  return null;
}

export async function readWorkspaceJson(
  userId: string,
  filePath: string
): Promise<unknown | null> {
  if (!isApplicationDatabaseConfigured()) return null;
  const parsed = parseWorkspaceDataPath(userId, filePath);
  if (!parsed) return null;

  switch (parsed.kind) {
    case "report":
      return readReportArtifact(userId, parsed.ticker, parsed.key);
    case "portfolio":
      return readPortfolio(userId);
    case "strategy": {
      const record = await readStrategy(userId, parsed.ticker);
      return record ? renderStrategyJson(record) : null;
    }
    default:
      return null;
  }
}

export async function writeWorkspaceJson(
  userId: string,
  filePath: string,
  value: unknown
): Promise<boolean> {
  if (!isApplicationDatabaseConfigured()) return false;
  const parsed = parseWorkspaceDataPath(userId, filePath);
  if (!parsed) return false;

  switch (parsed.kind) {
    case "report":
      await writeReportArtifact(userId, parsed.ticker, parsed.key, value);
      return true;
    case "portfolio":
      await writePortfolio(userId, value as Parameters<typeof writePortfolio>[1]);
      return true;
    case "strategy": {
      const strategy = StrategySchema.parse(value);
      await writeStrategy(strategyToWriteInput(strategy, userId));
      return true;
    }
    default:
      return false;
  }
}

export async function readWorkspaceText(
  userId: string,
  filePath: string,
  maxChars = 4000
): Promise<string | null> {
  if (!isApplicationDatabaseConfigured()) return null;
  const parsed = parseWorkspaceDataPath(userId, filePath);
  if (parsed?.kind !== "persona") return null;
  const text = await readPersonaMd(userId);
  return text ? text.slice(0, maxChars) : null;
}

export async function writeWorkspaceText(
  userId: string,
  filePath: string,
  text: string
): Promise<boolean> {
  if (!isApplicationDatabaseConfigured()) return false;
  const parsed = parseWorkspaceDataPath(userId, filePath);
  if (parsed?.kind !== "persona") return false;
  await writePersonaMd(userId, text);
  return true;
}


export async function writeGlobalReportArtifact(
  userId: string,
  artifactKey: string,
  payload: unknown
): Promise<void> {
  await writeReportArtifact(userId, GLOBAL_TICKER, artifactKey, payload);
}

export async function readGlobalReportArtifact(
  userId: string,
  artifactKey: string
): Promise<unknown | null> {
  return readReportArtifact(userId, GLOBAL_TICKER, artifactKey);
}
