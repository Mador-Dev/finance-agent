import type { Request, Response, NextFunction } from "express";
import bcrypt from "bcryptjs";
import { getAuth } from "@clerk/express";

export interface AuthenticatedRequest extends Request {
  userId?: string;
}

export function authMiddleware(
  req: AuthenticatedRequest,
  res: Response,
  next: NextFunction
): void {
  const authHeader = req.headers["authorization"];
  if (!authHeader || !authHeader.startsWith("Bearer ")) {
    res.status(401).json({ error: "unauthorized" });
    return;
  }

  const { userId } = getAuth(req);
  if (!userId) {
    res.status(401).json({ error: "unauthorized" });
    return;
  }
  res.locals["userId"] = userId;
  next();
}

export async function hashPassword(password: string): Promise<string> {
  return bcrypt.hash(password, 12);
}

export async function verifyPassword(password: string, hash: string): Promise<boolean> {
  return bcrypt.compare(password, hash);
}
