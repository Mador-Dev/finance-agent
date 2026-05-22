import { isFeatureEnabled } from "../featureFlagService.js";

export function isStepQueueServiceEnabled(): boolean {
  const raw = process.env["USE_STEP_QUEUE"];
  if (raw === undefined) return true;
  return !["0", "false", "no", "off"].includes(raw.trim().toLowerCase());
}

export async function isStepQueueEnabledForUser(userId: string): Promise<boolean> {
  if (isStepQueueServiceEnabled()) return true;
  return isFeatureEnabled("use_step_queue", userId);
}
