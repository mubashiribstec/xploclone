import { NextResponse } from "next/server";
import { SESSION_COOKIE } from "@/lib/web-auth";

// POST /api/auth/logout — clears the session cookie and sends the
// browser back to /login.
export async function POST(req: Request) {
  const res = NextResponse.redirect(new URL("/login", req.url));
  res.cookies.set(SESSION_COOKIE, "", { httpOnly: true, sameSite: "strict", path: "/", maxAge: 0 });
  return res;
}
