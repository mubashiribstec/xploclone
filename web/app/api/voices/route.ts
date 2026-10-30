import { NextResponse } from "next/server";

// Public voice list, proxied server-side (no API key needed for this route).
const API_URL = process.env.XPLOCLONE_API_URL ?? "http://localhost:8000";

export async function GET() {
  const res = await fetch(`${API_URL}/v1/voices`);
  if (!res.ok) {
    return NextResponse.json({ voices: [] }, { status: res.status });
  }
  return NextResponse.json(await res.json());
}
