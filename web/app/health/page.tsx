"use client";

import { useCallback, useEffect, useState } from "react";
import { Badge } from "@/components/ui";

type Health = {
  status?: string;
  ready?: boolean;
  version?: string;
  device?: string;
  engine?: string;
  chatterbox_revision?: string;
  chatterbox_revision_resolved?: string | null;
  engines?: Record<string, string>;
  voices?: Record<string, string>;
};

// Health page: live API /health via the /api/health proxy, with a
// working Refresh button and a last-checked timestamp.
export default function HealthPage() {
  const [health, setHealth] = useState<Health | null>(null);
  const [state, setState] = useState<"loading" | "ok" | "error">("loading");
  const [error, setError] = useState("");
  const [checkedAt, setCheckedAt] = useState("");

  const load = useCallback(async () => {
    setState("loading");
    setError("");
    try {
      const res = await fetch("/api/health");
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(typeof body?.detail === "string" ? body.detail : `API returned ${res.status}`);
      }
      setHealth((await res.json()) as Health);
      setState("ok");
      setCheckedAt(new Date().toLocaleString());
    } catch (e) {
      setHealth(null);
      setState("error");
      setError(e instanceof Error ? e.message : "Could not reach the API. Is the API server running?");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const rows: { label: string; value: string; tone?: "green" | "amber" | "grey" }[] = health
    ? [
        { label: "Liveness", value: health.status ?? "unknown", tone: health.status === "ok" ? "green" : "amber" },
        { label: "Ready", value: health.ready === undefined ? "—" : health.ready ? "yes" : "no", tone: health.ready ? "green" : "amber" },
        { label: "Version", value: health.version ?? "—" },
        { label: "Device", value: health.device ?? "—" },
        { label: "Engine", value: health.engine ?? "—" },
        { label: "Chatterbox revision (pinned)", value: health.chatterbox_revision ?? "—" },
        { label: "Chatterbox revision (loaded)", value: health.chatterbox_revision_resolved ?? "not loaded" },
        ...Object.entries(health.engines ?? {}).map(([k, v]) => ({ label: `Engine ${k}`, value: v })),
        ...Object.entries(health.voices ?? {}).map(([k, v]) => ({
          label: `Voice ${k}`,
          value: v,
          tone: (v === "loaded" ? "green" : "amber") as "green" | "amber",
        })),
      ]
    : [];

  return (
    <main className="mx-auto max-w-6xl px-4 py-8 sm:py-10">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">Health</h1>
          <p className="mt-1 text-sm text-zinc-600">
            Live status from the API&apos;s <code className="rounded bg-zinc-100 px-1">GET /health</code>.
            Liveness is always reported; readiness means an engine is loaded.
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
      {state === "loading" && !health ? (
        <p className="mt-6 text-sm text-zinc-500">Checking API health…</p>
      ) : (
        health && (
          <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {rows.map((r) => (
              <div key={r.label} className="rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm">
                <div className="text-xs font-medium uppercase tracking-wide text-zinc-500">{r.label}</div>
                <div className="mt-1 flex flex-wrap items-center justify-between gap-2">
                  <span className="break-all font-mono text-sm">{r.value}</span>
                  {r.tone && <Badge tone={r.tone}>{r.value}</Badge>}
                </div>
              </div>
            ))}
          </div>
        )
      )}
      <p className="mt-6 text-sm text-zinc-600">
        Docker / GPU status is not shown here — Docker builds and GPU inference are
        still unverified in this environment (see docs/BUILD-LOG.md).
      </p>
    </main>
  );
}
