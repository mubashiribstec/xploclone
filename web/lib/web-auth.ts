import { createHash, createHmac, timingSafeEqual } from "crypto";

// Single-owner web login (M1 fix). The web UI is an admin UI, not a
// public service: every page under (admin) and every /api/* proxy route
// requires a valid session cookie. There is no signup and no per-user
// account — one owner password, set via XPLOCLONE_WEB_PASSWORD_HASH
// (SHA-256 hex of the password). The session cookie is an HMAC of a
// fixed string under XPLOCLONE_WEB_SESSION_SECRET, so it is verifiable
// without a session store. If either variable is empty, logins are
// refused — there is no default password and no bypass.

export const SESSION_COOKIE = "xploclone-web-session";
const SESSION_LABEL = "xploclone-web-session-v1";

function safeEqual(a: string, b: string): boolean {
  const ab = Buffer.from(a);
  const bb = Buffer.from(b);
  return ab.length === bb.length && timingSafeEqual(ab, bb);
}

export function hashPassword(password: string): string {
  return createHash("sha256").update(password, "utf8").digest("hex");
}

export function verifyPassword(password: string): boolean {
  const expected = (process.env.XPLOCLONE_WEB_PASSWORD_HASH ?? "").trim().toLowerCase();
  if (!expected || !password) return false;
  return safeEqual(hashPassword(password), expected);
}

export function createSessionToken(): string | null {
  const secret = process.env.XPLOCLONE_WEB_SESSION_SECRET ?? "";
  if (!secret) return null;
  return createHmac("sha256", secret).update(SESSION_LABEL).digest("hex");
}

export function verifySession(token: string | undefined | null): boolean {
  if (!token) return false;
  const expected = createSessionToken();
  if (!expected) return false;
  return safeEqual(token, expected);
}
