import { NextResponse } from "next/server";
import { SESSION_COOKIE, createSessionToken, verifyPassword } from "@/lib/web-auth";

// POST /api/auth/login { password } — single-owner login (M1).
// Sets an httpOnly session cookie. No password is ever returned or logged.
export async function POST(req: Request) {
  const body = await req.json().catch(() => null);
  const password = typeof body?.password === "string" ? body.password : "";
  if (!verifyPassword(password)) {
    return NextResponse.json({ detail: "Invalid password." }, { status: 401 });
  }
  const token = createSessionToken();
  if (!token) {
    return NextResponse.json(
      { detail: "Web session is not configured on this server." },
      { status: 503 },
    );
  }
  const res = NextResponse.json({ ok: true });
  res.cookies.set(SESSION_COOKIE, token, {
    httpOnly: true,
    sameSite: "strict",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: 12 * 60 * 60, // 12 hours
  });
  return res;
}
