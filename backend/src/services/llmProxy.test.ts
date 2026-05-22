import test from "node:test";
import assert from "node:assert/strict";
import { generateProxyKey, toProxyModel } from "./llmProxy.js";

test("generateProxyKey creates a stable per-user proxy key", () => {
  const previousSecret = process.env["JWT_SECRET"];
  process.env["JWT_SECRET"] = "test-secret";

  try {
    const first = generateProxyKey("neta");
    const second = generateProxyKey("neta");

    assert.equal(first, second);
    assert.match(first, /^clawd-sk-neta-[a-f0-9]{32}$/);
    assert.notEqual(first, generateProxyKey("other-user"));
  } finally {
    if (previousSecret === undefined) {
      delete process.env["JWT_SECRET"];
    } else {
      process.env["JWT_SECRET"] = previousSecret;
    }
  }
});

test("toProxyModel wraps OpenRouter model ids with the synthetic per-user prefix", () => {
  assert.equal(
    toProxyModel("neta", "openrouter/google/gemini-2.5-flash"),
    "clawd-neta/google/gemini-2.5-flash"
  );
  assert.equal(
    toProxyModel("neta", "google/gemini-2.5-flash"),
    "google/gemini-2.5-flash"
  );
});
