import { NextResponse } from "next/server";
import { requireWebSession } from "@/lib/web-rate-limit";

// Voice list, proxied server-side (no API key needed for this route).
// Requires a valid owner web session (M1) — the list is part of the admin UI.
const API_URL = process.env.XPLOCLONE_API_URL ?? "http://localhost:8000";

export async function GET(req: Request) {
  const session = requireWebSession(req);
  if (!session.ok) {
    return NextResponse.json({ detail: "Web login required." }, { status: session.status });
  }
  let res: Response;
  try {
    res = await fetch(`${API_URL}/v1/voices`);
  } catch {
    return NextResponse.json({ voices: [] }, { status: 502 });
  }
  if (!res.ok) {
    return NextResponse.json({ voices: [] }, { status: res.status });
  }
  return NextResponse.json(await res.json());
}
