import { NextResponse } from "next/server";

// Server-side proxy: the browser never talks to the GPU server and the
// API key never ships to the browser. Both values come from the server
// environment only.
const API_URL = process.env.XPLOCLONE_API_URL ?? "http://localhost:8000";
const API_KEY = process.env.XPLOCLONE_API_KEY ?? "";

export async function POST(req: Request) {
  const body = await req.json().catch(() => null);
  if (!body || typeof body.voice_id !== "string" || typeof body.text !== "string") {
    return NextResponse.json({ detail: "voice_id and text are required." }, { status: 400 });
  }
  const res = await fetch(`${API_URL}/v1/tts`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${API_KEY}`,
    },
    body: JSON.stringify({ voice_id: body.voice_id, text: body.text, format: "wav" }),
  });
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
      "X-Watermark": res.headers.get("X-Watermark") ?? "",
    },
  });
}
