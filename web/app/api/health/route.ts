import { NextResponse } from "next/server";
import { requireWebSession } from "@/lib/web-rate-limit";

// GET /api/health — server-side proxy for the Health page's Refresh
// button. The browser never talks to the API directly. Requires a
// valid owner web session; the API itself is unauthenticated on /health.
const API_URL = process.env.XPLOCLONE_API_URL ?? "http://localhost:8000";

export async function GET(req: Request) {
  const session = requireWebSession(req);
  if (!session.ok) {
    return NextResponse.json({ detail: "Web login required." }, { status: session.status });
  }
  try {
    const res = await fetch(`${API_URL}/health`, { cache: "no-store" });
    if (!res.ok) {
      return NextResponse.json({ detail: `API returned ${res.status}.` }, { status: 502 });
    }
    return NextResponse.json(await res.json());
  } catch {
    return NextResponse.json({ detail: "API unavailable." }, { status: 502 });
  }
}
