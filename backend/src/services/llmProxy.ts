// backend/src/services/llmProxy.ts
// Temporary advisor routing helpers retained after the OpenClaw /llm/v1 route was retired.

import crypto from "crypto";

export const PROXY_BASE_URL =
  process.env["LLM_PROXY_URL"] ?? "http://localhost:8081/llm/v1";

export function generateProxyKey(userId: string): string {
  const secret = process.env["JWT_SECRET"] ?? "changeme";
  const hmac = crypto.createHmac("sha256", secret).update(userId).digest("hex");
  return `clawd-sk-${userId}-${hmac.slice(0, 32)}`;
}

export function toProxyModel(userId: string, model: string): string {
  if (model.startsWith("openrouter/")) {
    return `clawd-${userId}/${model.slice("openrouter/".length)}`;
  }
  return model;
}
