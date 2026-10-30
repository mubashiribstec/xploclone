import { headers } from "next/headers";

type Voice = {
  voice_id: string;
  language: string;
  accent: string;
  engine: string;
  status: "loaded" | "unavailable";
  description: string;
};

// Voices page (M6): the 3 hardcoded voices, with live status from the API.
// No voice can be created, deleted, or uploaded here — by design (PLAN-v2 §2.1).
export default async function VoicesPage() {
  const apiUrl = process.env.XPLOCLONE_API_URL ?? "http://localhost:8000";
  let voices: Voice[] = [];
  let error = "";
  try {
    const res = await fetch(`${apiUrl}/v1/voices`, { cache: "no-store" });
    if (!res.ok) throw new Error(`API returned ${res.status}`);
    voices = (await res.json()).voices ?? [];
  } catch {
    error = "Could not reach the API. Is the API server running?";
  }
  // Keep the import used on the server (headers are awaited by Next).
  await headers();

  return (
    <main className="mx-auto max-w-2xl px-4 py-10">
      <h1 className="text-2xl font-bold">Voices</h1>
      <p className="mt-1 text-sm text-zinc-600">
        Only Mubashir Ali&apos;s voice, in three variants at most. No other voice can be
        added — there is no upload or create endpoint.
      </p>
      {error && <p className="mt-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}
      <ul className="mt-6 space-y-3">
        {voices.map((v) => (
          <li key={v.voice_id} className="rounded-lg border border-zinc-200 bg-white p-4 text-sm">
            <div className="font-medium">
              {v.voice_id} · {v.language} ({v.accent})
            </div>
            <div className="text-zinc-600">{v.description}</div>
            <div className="mt-1 text-xs text-zinc-500">
              Engine: {v.engine} · Status:{" "}
              <span className={v.status === "loaded" ? "text-green-700" : "text-amber-700"}>
                {v.status}
              </span>
            </div>
          </li>
        ))}
      </ul>
      <p className="mt-6 text-sm text-zinc-600">
        A voice reports <code>unavailable</code> until its reference recording is on the
        server (see <code>docs/recording-scripts/</code>). Urdu reports unavailable until
        the gated spike in <code>docs/URDU-SPIKE.md</code> passes.
      </p>
    </main>
  );
}
