// API keys page (M6): keys are env-managed in v1 — there is no
// create/revoke UI. This page shows only whether each credential is
// configured (never its value) and how to rotate it.
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

  return (
    <main className="mx-auto max-w-2xl px-4 py-10">
      <h1 className="text-2xl font-bold">API keys</h1>
      <p className="mt-1 text-sm text-zinc-600">
        Keys are managed in the server environment (<code>.env</code>), not in this UI.
        Rotating a key means generating a new value, updating <code>.env</code>, and
        restarting the API / web services. No key value is ever displayed here.
      </p>
      <ul className="mt-6 space-y-3">
        {rows.map((r) => (
          <li key={r.name} className="rounded-lg border border-zinc-200 bg-white p-4 text-sm">
            <div className="font-medium">{r.name}</div>
            <div className={r.configured ? "text-green-700" : "text-red-700"}>
              {r.configured ? "Configured" : "Not configured"}
            </div>
            <div className="mt-1 text-zinc-600">{r.note}</div>
          </li>
        ))}
      </ul>
      <p className="mt-6 text-sm text-zinc-600">
        Limits: 60 requests/minute per API key, 1 concurrent synthesis (PLAN-v2 §6.4).
        A leaked key must be rotated immediately — revocation is by replacement.
      </p>
    </main>
  );
}
