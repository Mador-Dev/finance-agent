import "reflect-metadata";
import { promises as fs } from "fs";
import path from "path";
import { DataSource } from "typeorm";
import { JobEntitySchema } from "./entities/JobEntity.js";
import { TrackedAssetEntitySchema } from "./entities/TrackedAssetEntity.js";
import { UserEntitySchema } from "./entities/UserEntity.js";
import { StrategyEntitySchema } from "./entities/StrategyEntity.js";
import { NotificationEntitySchema } from "./entities/NotificationEntity.js";
import { VerdictActionEntitySchema } from "./entities/VerdictActionEntity.js";
import { TickerSnoozeEntitySchema } from "./entities/TickerSnoozeEntity.js";
import { ConversationEntitySchema } from "./entities/ConversationEntity.js";
import { logger } from "../services/logger.js";

const APP_DATABASE_URL =
  process.env["APP_DATABASE_URL"] ??
  process.env["OBSERVABILITY_DATABASE_URL"] ??
  "";
const APP_DATABASE_DDL_PATH =
  process.env["APP_DATABASE_DDL_PATH"] ??
  process.env["OBSERVABILITY_DDL_PATH"] ??
  path.resolve(process.cwd(), "../db/application_postgres.sql");

let dataSource: DataSource | null = null;
let ddlApplied = false;

export function isApplicationDatabaseConfigured(): boolean {
  return APP_DATABASE_URL.length > 0;
}

function buildDataSource(): DataSource {
  if (!APP_DATABASE_URL) {
    throw new Error("APP_DATABASE_URL is required");
  }

  const urlWithoutSsl = APP_DATABASE_URL
    .replace(/[?&]sslmode=[^&]*/g, "")
    .replace(/[?&]uselibpqcompat=[^&]*/g, "")
    .replace(/\?&/, "?")
    .replace(/[?&]$/, "");

  return new DataSource({
    type: "postgres",
    url: urlWithoutSsl,
    ssl: false,
    extra: { ssl: false },
    entities: [
      JobEntitySchema,
      TrackedAssetEntitySchema,
      UserEntitySchema,
      StrategyEntitySchema,
      NotificationEntitySchema,
      VerdictActionEntitySchema,
      TickerSnoozeEntitySchema,
      ConversationEntitySchema,
    ],
    synchronize: false,
    logging: false,
  });
}

async function applyDdl(ds: DataSource): Promise<void> {
  if (ddlApplied) return;
  const ddl = await fs.readFile(APP_DATABASE_DDL_PATH, "utf-8");
  await ds.query(ddl);
  ddlApplied = true;
  logger.info(`Applied application DDL from ${APP_DATABASE_DDL_PATH}`);
}

export async function getApplicationDataSource(): Promise<DataSource> {
  if (!dataSource) {
    dataSource = buildDataSource();
  }

  if (!dataSource.isInitialized) {
    await dataSource.initialize();
    await applyDdl(dataSource);
    logger.info("Application PostgreSQL data source initialized");
  }

  return dataSource;
}

export async function closeApplicationDataSource(): Promise<void> {
  if (dataSource?.isInitialized) {
    await dataSource.destroy();
  }
  dataSource = null;
  ddlApplied = false;
}
