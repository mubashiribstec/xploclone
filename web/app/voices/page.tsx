"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Badge } from "@/components/ui";

type Voice = {
  voice_id: string;
  language: string;
  accent: string;
  engine: string;
  status: "loaded" | "unavailable";
  description: string;
};

// Voices page: the 3 hardcoded voices, with live status from the API
// via the /api/voices proxy. No voice can be created, deleted, or
// uploaded here — by design (PLAN-v2 §2.1).
export default function VoicesPage() {
  const router = useRouter();
  const [voices, setVoices] = useState<Voice[]>([]);
  const [state, setState] = useState<"loading" | "ok" | "error">("loading");
  const [error, setError] = useState("");
  const [checkedAt, setCheckedAt] = useState("");

  const load = useCallback(async () => {
    setState("loading");
    setError("");
    try {
      const res = await fetch("/api/voices");
      if (!res.ok) throw new Error(`API returned ${res.status}`);
      const d = await res.json();
      setVoices((d.voices ?? []) as Voice[]);
      setState("ok");
      setCheckedAt(new Date().toLocaleString());
    } catch {
      setVoices([]);
      setState("error");
      setError("Could not reach the API. Is the API server running? Check the Health page, then retry.");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <main className="mx-auto max-w-6xl px-4 py-8 sm:py-10">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">Voices</h1>
          <p className="mt-1 text-sm text-zinc-600">
            Only Mubashir Ali&apos;s voice, in three variants at most. No other voice can be
            added — there is no upload or create endpoint.
          </p>
        </div>
        <button
          type="button"
          onClick={() => void load()}
          disabled={state === "loading"}
          className="rounded-lg border border-zinc-300 bg-white px-4 py-2 text-sm font-medium text-zinc-700 hover:bg-zinc-50 disabled:opacity-50"
        >
          {state === "loading" ? "Refreshing…" : "Refresh"}
        </button>
      </div>
      {checkedAt && state === "ok" && (
        <p className="mt-2 text-xs text-zinc-500">Last checked: {checkedAt}</p>
      )}
      {error && (
        <div role="alert" className="mt-5 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">
          <span>{error}</span>
          <button
            type="button"
            onClick={() => void load()}
            className="rounded-lg bg-red-700 px-3 py-1.5 text-xs font-medium text-white hover:bg-red-800"
          >
            Retry
          </button>
        </div>
      )}
      {state === "loading" && voices.length === 0 ? (
        <p className="mt-6 text-sm text-zinc-500">Loading voices…</p>
      ) : (
        <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {voices.map((v) => {
            const loaded = v.status === "loaded";
            const isUrdu = v.voice_id === "mubashir-ur";
            return (
              <article key={v.voice_id} className="flex flex-col rounded-2xl border border-zinc-200 bg-white p-5 shadow-sm">
                <div className="flex items-start justify-between gap-2">
                  <h2 className="text-base font-semibold">
                    {v.language === "en-US" ? "🇺🇸 English (US)" : v.language === "en-GB" ? "🇬🇧 English (British)" : "🇵🇰 Urdu"}
                  </h2>
                  <Badge tone={loaded ? "green" : isUrdu ? "grey" : "amber"}>
                    {loaded ? "Ready" : isUrdu ? "In research" : "Unavailable"}
                  </Badge>
                </div>
                <p className="mt-1 font-mono text-xs text-zinc-500">{v.voice_id}</p>
                <p className="mt-2 flex-1 text-sm text-zinc-600">{v.description}</p>
                <dl className="mt-4 space-y-1 border-t border-zinc-100 pt-3 text-xs text-zinc-500">
                  <div className="flex justify-between"><dt>Language</dt><dd>{v.language} ({v.accent})</dd></div>
                  <div className="flex justify-between"><dt>Engine</dt><dd>{v.engine}</dd></div>
                  <div className="flex justify-between"><dt>Status</dt><dd>{v.status}</dd></div>
                </dl>
                {isUrdu ? (
                  <p className="mt-4 rounded-lg bg-zinc-100 p-3 text-xs text-zinc-600">
                    Urdu generation is disabled until the gated spike in{" "}
                    <code>docs/URDU-SPIKE.md</code> passes — there is no engine to test yet.
                  </p>
                ) : (
                  <button
                    type="button"
                    onClick={() => router.push(`/?voice=${encodeURIComponent(v.voice_id)}`)}
                    disabled={!loaded}
                    title={loaded ? `Use ${v.voice_id} in Generate` : "Unavailable — no reference recording on the server yet."}
                    className="mt-4 w-full rounded-lg bg-zinc-900 px-4 py-2 text-sm font-medium text-white hover:bg-zinc-800 disabled:cursor-not-allowed disabled:opacity-40"
                  >
                    {loaded ? "Use this voice →" : "Unavailable — no recording yet"}
                  </button>
                )}
              </article>
            );
          })}
        </div>
      )}
      {state === "ok" && voices.length === 0 && (
        <p className="mt-6 rounded-xl border border-zinc-200 bg-white p-4 text-sm text-zinc-600">
          The API returned no voices. That is unexpected — the API always returns the 3
          hardcoded voices. Check the Health page.
        </p>
      )}
      <p className="mt-6 text-sm text-zinc-600">
        A voice reports <code className="rounded bg-zinc-100 px-1">unavailable</code> until
        its reference recording is on the server (see{" "}
        <code className="rounded bg-zinc-100 px-1">docs/recording-scripts/</code>). Urdu
        reports unavailable until the gated spike in{" "}
        <code className="rounded bg-zinc-100 px-1">docs/URDU-SPIKE.md</code> passes.
      </p>
    </main>
  );
}
