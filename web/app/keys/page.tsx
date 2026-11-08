import { Badge, CopyButton } from "@/components/ui";

// API keys page: keys are env-managed in v1 — there is no
// create/revoke UI. This page shows only whether each credential is
// configured (never its value) and how to rotate it. Copy buttons
// copy the endpoint URL and a curl example (no secret in either).
export default function KeysPage() {
  const apiKeySet = Boolean(process.env.XPLOCLONE_API_KEY);
  const apiHashSet = Boolean(process.env.XPLOCLONE_API_KEY_HASH);
  const webPasswordSet = Boolean(process.env.XPLOCLONE_WEB_PASSWORD_HASH);
  const sessionSecretSet = Boolean(process.env.XPLOCLONE_WEB_SESSION_SECRET);

  const rows: { name: string; configured: boolean; note: string }[] = [
    {
      name: "Admin API key (XPLOCLONE_API_KEY)",
      configured: apiKeySet,
      note: "Plaintext key for the server-side proxy only. Never shown here, never in git.",
    },
    {
      name: "Admin API key hash (XPLOCLONE_API_KEY_HASH)",
      configured: apiHashSet,
      note: "SHA-256 hex the API compares against. Generate with: python -c \"import hashlib; print(hashlib.sha256(b'YOUR_KEY').hexdigest())\"",
    },
    {
      name: "Web UI password hash (XPLOCLONE_WEB_PASSWORD_HASH)",
      configured: webPasswordSet,
      note: "SHA-256 hex of the owner password for this admin UI.",
    },
    {
      name: "Web session secret (XPLOCLONE_WEB_SESSION_SECRET)",
      configured: sessionSecretSet,
      note: "Random secret that signs the web session cookie.",
    },
  ];

  const curlExample = `curl -X POST http://127.0.0.1:8000/v1/tts \\
  -H "Authorization: Bearer $XPLOCLONE_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{"voice_id":"mubashir-en-gb","text":"Hello, thank you for calling.","format":"wav"}' \\
  --output out.wav`;

  return (
    <main className="mx-auto max-w-6xl px-4 py-8 sm:py-10">
      <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">API keys</h1>
      <p className="mt-1 max-w-3xl text-sm text-zinc-600">
        Keys are managed in the server environment (<code className="rounded bg-zinc-100 px-1">.env</code>), not in this UI.
        Rotating a key means generating a new value, updating{" "}
        <code className="rounded bg-zinc-100 px-1">.env</code>, and restarting the API /
        web services. No key value is ever displayed here.
      </p>

      <div className="mt-6 grid gap-4 sm:grid-cols-2">
        {rows.map((r) => (
          <article key={r.name} className="rounded-2xl border border-zinc-200 bg-white p-5 shadow-sm">
            <div className="flex items-start justify-between gap-2">
              <h2 className="text-sm font-semibold">{r.name}</h2>
              <Badge tone={r.configured ? "green" : "red"}>
                {r.configured ? "Configured" : "Not configured"}
              </Badge>
            </div>
            <p className="mt-2 text-sm text-zinc-600">{r.note}</p>
          </article>
        ))}
      </div>

      <section aria-labelledby="endpoint-heading" className="mt-6 rounded-2xl border border-zinc-200 bg-white p-5 shadow-sm sm:p-6">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 id="endpoint-heading" className="text-base font-semibold">Use the API from your own products</h2>
          <CopyButton text="http://127.0.0.1:8000/v1/tts" label="Copy endpoint URL" />
        </div>
        <p className="mt-2 text-sm text-zinc-600">
          Base URL (local): <code className="rounded bg-zinc-100 px-1">http://127.0.0.1:8000</code>.
          The browser never calls this directly — the web UI proxies through its own{" "}
          <code className="rounded bg-zinc-100 px-1">/api/*</code> routes. This curl example
          is for your own server (Xplogent, xplosole). It contains no secret — replace{" "}
          <code className="rounded bg-zinc-100 px-1">$XPLOCLONE_API_KEY</code> with the real
          key from <code className="rounded bg-zinc-100 px-1">.env</code>.
        </p>
        <div className="mt-4 flex items-start justify-between gap-2">
          <pre className="flex-1 overflow-x-auto rounded-xl bg-zinc-900 p-4 text-xs leading-relaxed text-zinc-100">
            {curlExample}
          </pre>
        </div>
        <div className="mt-3">
          <CopyButton text={curlExample} label="Copy curl example" />
        </div>
      </section>

      <section aria-labelledby="rotate-heading" className="mt-6 rounded-2xl border border-zinc-200 bg-white p-5 shadow-sm sm:p-6">
        <h2 id="rotate-heading" className="text-base font-semibold">How to rotate a key</h2>
        <ol className="mt-3 list-decimal space-y-1.5 pl-5 text-sm text-zinc-600">
          <li>Generate a new key: <code className="rounded bg-zinc-100 px-1">python3 -c &quot;import secrets; print(secrets.token_hex(32))&quot;</code></li>
          <li>Generate its hash: <code className="rounded bg-zinc-100 px-1">python3 -c &quot;import hashlib; print(hashlib.sha256(b&apos;YOUR_KEY&apos;).hexdigest())&quot;</code></li>
          <li>Update <code className="rounded bg-zinc-100 px-1">XPLOCLONE_API_KEY</code> and <code className="rounded bg-zinc-100 px-1">XPLOCLONE_API_KEY_HASH</code> in <code className="rounded bg-zinc-100 px-1">.env</code>.</li>
          <li>Restart the API and web services: <code className="rounded bg-zinc-100 px-1">docker compose up --build -d</code></li>
        </ol>
        <p className="mt-3 text-sm text-zinc-600">
          Limits: 60 requests/minute per API key, 1 concurrent synthesis (PLAN-v2 §6.4).
          A leaked key must be rotated immediately — revocation is by replacement.
        </p>
      </section>
    </main>
  );
}
