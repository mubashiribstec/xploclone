import { createHmac, timingSafeEqual } from "node:crypto";
import { NextResponse, type NextRequest } from "next/server";

// Next.js 16 "proxy" (formerly middleware) — M1 fix.
// Every request except /login and /api/auth/* requires a valid owner
// session cookie. Unauthenticated requests are redirected to /login.
// The session check is self-contained here (HMAC of a fixed string
// under XPLOCLONE_WEB_SESSION_SECRET) so the proxy does not depend on
// shared app modules. The /api/* proxy routes check the session again
// themselves (defence in depth) and rate-limit per session.
const SESSION_COOKIE = "xploclone-web-session";
const SESSION_LABEL = "xploclone-web-session-v1";

function verifySession(token: string | undefined): boolean {
  if (!token) return false;
  const secret = process.env.XPLOCLONE_WEB_SESSION_SECRET ?? "";
  if (!secret) return false;
  const expected = createHmac("sha256", secret).update(SESSION_LABEL).digest("hex");
  const a = Buffer.from(token);
  const b = Buffer.from(expected);
  return a.length === b.length && timingSafeEqual(a, b);
}

export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const publicPaths = ["/login", "/api/auth/login", "/api/auth/logout"];
  if (publicPaths.includes(pathname)) return NextResponse.next();
  if (verifySession(request.cookies.get(SESSION_COOKIE)?.value)) {
    return NextResponse.next();
  }
  // API clients get a 401, not a login-page redirect.
  if (pathname.startsWith("/api/")) {
    return NextResponse.json({ detail: "Web login required." }, { status: 401 });
  }
  return NextResponse.redirect(new URL("/login", request.url));
}

export const config = {
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp|ico)$).*)",
  ],
};
