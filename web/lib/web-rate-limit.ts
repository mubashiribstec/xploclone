// Per-session rate limiting for the web proxy (M1 fix).
// The API's 60 req/min limit is per shared server key, so all web users
// would share one bucket. This limiter runs per web session cookie, so
// one session cannot starve the others. In-memory, single instance —
// acceptable for a single-owner admin UI; it resets on restart.

import { SESSION_COOKIE, verifySession } from "./web-auth";

const hits = new Map<string, number[]>();

export function allowSession(key: string, perMin = 60, windowS = 60): { allowed: boolean; retryAfter: number } {
  const now = Date.now() / 1000;
  const list = (hits.get(key) ?? []).filter((t) => t > now - windowS);
  if (list.length >= perMin) {
    return { allowed: false, retryAfter: Math.max(1, Math.ceil(windowS - (now - list[0]))) };
  }
  list.push(now);
  hits.set(key, list);
  return { allowed: true, retryAfter: 0 };
}

export function requireWebSession(req: Request): { ok: true; session: string } | { ok: false; status: number } {
  const cookie = req.headers.get("cookie") ?? "";
  const token = cookie
    .split(";")
    .map((p) => p.trim())
    .find((p) => p.startsWith(`${SESSION_COOKIE}=`))
    ?.slice(SESSION_COOKIE.length + 1);
  if (!verifySession(token)) return { ok: false, status: 401 };
  return { ok: true, session: token as string };
}
