import { NextResponse } from "next/server";
import { allowSession, requireWebSession } from "@/lib/web-rate-limit";

// Server-side proxy: the browser never talks to the GPU server and the
// API key never ships to the browser. Both values come from the server
// environment only. Requires a valid owner web session (M1) and is
// rate-limited per session, not just per shared server key.
const API_URL = process.env.XPLOCLONE_API_URL ?? "http://localhost:8000";
const API_KEY = process.env.XPLOCLONE_API_KEY ?? "";

export async function POST(req: Request) {
  const session = requireWebSession(req);
  if (!session.ok) {
    return NextResponse.json({ detail: "Web login required." }, { status: session.status });
  }
  const limited = allowSession(session.session);
  if (!limited.allowed) {
    return NextResponse.json(
      { detail: "Web rate limit exceeded (60 req/min per session)." },
      { status: 429, headers: { "Retry-After": String(limited.retryAfter) } },
    );
  }
  const body = await req.json().catch(() => null);
  if (!body || typeof body.voice_id !== "string" || typeof body.text !== "string") {
    return NextResponse.json({ detail: "voice_id and text are required." }, { status: 400 });
  }
  // Forward prosody fields when present (validated server-side by the
  // API: unknown preset -> 400, out-of-range knob -> 422). Only known
  // fields are forwarded — nothing else from the browser reaches the API.
  const forward: Record<string, unknown> = {
    voice_id: body.voice_id,
    text: body.text,
    format: "wav",
  };
  for (const key of ["preset", "style", "exaggeration", "cfg_weight", "temperature", "top_p", "repetition_penalty"]) {
    if (body[key] !== undefined) forward[key] = body[key];
  }
  let res: Response;
  try {
    res = await fetch(`${API_URL}/v1/tts`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${API_KEY}`,
      },
      body: JSON.stringify(forward),
    });
  } catch {
    return NextResponse.json({ detail: "API unavailable." }, { status: 502 });
  }
  if (!res.ok) {
    const detail = await res.json().catch(() => ({ detail: `API error ${res.status}` }));
    return NextResponse.json(detail, { status: res.status });
  }
  const buf = await res.arrayBuffer();
  return new NextResponse(buf, {
    status: 200,
    headers: {
      "Content-Type": "audio/wav",
      "X-XploClone-Voice": res.headers.get("X-XploClone-Voice") ?? "",
      "X-XploClone-Chars": res.headers.get("X-XploClone-Chars") ?? "",
      "X-XploClone-Latency-Ms": res.headers.get("X-XploClone-Latency-Ms") ?? "",
      "X-XploClone-Preset": res.headers.get("X-XploClone-Preset") ?? "",
      "X-Watermark": res.headers.get("X-Watermark") ?? "",
    },
  });
}
