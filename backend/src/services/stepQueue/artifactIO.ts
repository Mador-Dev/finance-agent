import { promises as fs } from "fs";
import { writeWorkspaceJson } from "../workspaceDataIO.js";

export async function atomicWriteJson(
  userId: string,
  filePath: string,
  value: unknown
): Promise<void> {
  const stored = await writeWorkspaceJson(userId, filePath, value);
  if (stored) return;

  const { randomUUID } = await import("crypto");
  const path = await import("path");
  await fs.mkdir(path.dirname(filePath), { recursive: true });
  const tmpPath = `${filePath}.${randomUUID()}.tmp`;
  const handle = await fs.open(tmpPath, "w");
  try {
    await handle.writeFile(JSON.stringify(value, null, 2), "utf-8");
    await handle.sync();
  } finally {
    await handle.close();
  }
  await fs.rename(tmpPath, filePath);
}
