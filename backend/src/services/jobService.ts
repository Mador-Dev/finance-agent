import { randomBytes } from "crypto";
import { logger } from "./logger.js";
import { JobSchema } from "../schemas/job.js";
import type { UserWorkspace } from "../middleware/userIsolation.js";
import type { Job, JobAction, JobSource } from "../types/index.js";
import {
  createJobInDb,
  getJobFromDb,
  isJobStoreAvailable,
  listJobsFromDb,
  updateJobInDb,
} from "./jobStore.js";

export class JobNotFoundError extends Error {
  constructor(jobId: string) {
    super(`Job not found: ${jobId}`);
    this.name = "JobNotFoundError";
  }
}

function generateJobId(): string {
  const now = new Date();
  const dateStr = now
    .toISOString()
    .replace(/[-:]/g, "")
    .slice(0, 15)
    .replace("T", "_");
  const hex = randomBytes(3).toString("hex");
  return `job_${dateStr}_${hex}`;
}

export async function createJob(
  workspace: UserWorkspace,
  action: JobAction,
  ticker?: string,
  options?: { source?: JobSource }
): Promise<Job> {
  if (!isJobStoreAvailable()) {
    throw new Error("APP_DATABASE_URL is required for job state");
  }

  const id = generateJobId();
  const triggered_at = new Date().toISOString();

  const job: Job = {
    id,
    action,
    ticker: ticker ?? null,
    source: options?.source ?? null,
    budget_admitted_at: null,
    status: "pending",
    triggered_at,
    started_at: null,
    completed_at: null,
    result: null,
    error: null,
  };

  await createJobInDb(workspace.userId, job);
  logger.info(`Job created: ${id} action=${action} ticker=${ticker ?? "none"}`);
  return job;
}

export async function getJob(workspace: UserWorkspace, jobId: string): Promise<Job> {
  if (!isJobStoreAvailable()) {
    throw new Error("APP_DATABASE_URL is required for job state");
  }
  const job = await getJobFromDb(workspace.userId, jobId);
  if (!job) throw new JobNotFoundError(jobId);
  return job;
}

export async function listJobs(workspace: UserWorkspace, limit = 50): Promise<Job[]> {
  if (!isJobStoreAvailable()) {
    throw new Error("APP_DATABASE_URL is required for job state");
  }
  return listJobsFromDb(workspace.userId, limit);
}

export async function hasPendingAgentManagedWork(
  _workspace: UserWorkspace
): Promise<boolean> {
  return false;
}

export async function updateJob(
  workspace: UserWorkspace,
  jobId: string,
  update: Partial<Pick<Job, "status" | "started_at" | "completed_at" | "result" | "error" | "budget_admitted_at">>
): Promise<Job> {
  if (!isJobStoreAvailable()) {
    throw new Error("APP_DATABASE_URL is required for job state");
  }

  const current = await getJob(workspace, jobId);
  const merged: Job = { ...current, ...update };
  const result = JobSchema.safeParse(merged);
  if (!result.success) {
    throw new Error(
      `Invalid job update: ${result.error.errors.map((e) => e.message).join("; ")}`
    );
  }

  const updated = await updateJobInDb(workspace.userId, jobId, update);
  if (!updated) throw new JobNotFoundError(jobId);
  logger.info(`Job updated: ${jobId} status=${updated.status}`);
  return updated;
}
