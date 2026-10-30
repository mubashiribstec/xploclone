import { headers } from "next/headers";

type Health = {
  status?: string;
  ready?: boolean;
  version?: string;
  device?: string;
  chatterbox_revision?: string;
  chatterbox_revision_resolved?: string | null;
  engines?: Record<string, string>;
  voices?: Record<string, string>;
};

// Health page (M6): live API /health, rendered server-side.
export default async function HealthPage() {
  const apiUrl = process.env.XPLOCLONE_API_URL ?? "http://localhost:8000";
  let health: Health | null = null;
  let error = "";
  try {
    const res = await fetch(`${apiUrl}/health`, { cache: "no-store" });
    if (!res.ok) throw new Error(`API returned ${res.status}`);
    health = (await res.json()) as Health;
  } catch {
    error = "Could not reach the API. Is the API server running?";
  }
  await headers();

  return (
    <main className="mx-auto max-w-2xl px-4 py-10">
      <h1 className="text-2xl font-bold">Health</h1>
      <p className="mt-1 text-sm text-zinc-600">
        Live status from the API&apos;s <code>GET /health</code>. Liveness is always
        reported; readiness means an engine is loaded.
      </p>
      {error && <p className="mt-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}
      {health && (
        <dl className="mt-6 space-y-2 rounded-lg border border-zinc-200 bg-white p-4 text-sm">
          <div className="flex justify-between">
            <dt className="text-zinc-500">Liveness</dt>
            <dd>{health.status ?? "unknown"}</dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-zinc-500">Ready</dt>
            <dd>{health.ready === undefined ? "—" : health.ready ? "yes" : "no"}</dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-zinc-500">Version</dt>
            <dd>{health.version ?? "—"}</dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-zinc-500">Device</dt>
            <dd>{health.device ?? "—"}</dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-zinc-500">Chatterbox revision (pinned)</dt>
            <dd className="font-mono text-xs">{health.chatterbox_revision ?? "—"}</dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-zinc-500">Chatterbox revision (loaded)</dt>
            <dd className="font-mono text-xs">{health.chatterbox_revision_resolved ?? "not loaded"}</dd>
          </div>
          {health.engines &&
            Object.entries(health.engines).map(([k, v]) => (
              <div key={k} className="flex justify-between">
                <dt className="text-zinc-500">Engine {k}</dt>
                <dd>{v}</dd>
              </div>
            ))}
          {health.voices &&
            Object.entries(health.voices).map(([k, v]) => (
              <div key={k} className="flex justify-between">
                <dt className="text-zinc-500">Voice {k}</dt>
                <dd>{v}</dd>
              </div>
            ))}
        </dl>
      )}
      <p className="mt-6 text-sm text-zinc-600">
        Docker / GPU status is not shown here — Docker builds and GPU inference are
        still unverified in this environment (see docs/BUILD-LOG.md).
      </p>
    </main>
  );
}
