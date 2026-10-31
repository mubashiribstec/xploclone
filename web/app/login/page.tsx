"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

export default function LoginPage() {
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const router = useRouter();

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const res = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        setError(typeof body?.detail === "string" ? body.detail : "Login failed.");
        return;
      }
      router.push("/");
      router.refresh();
    } catch {
      setError("Network error — is the web server running?");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="mx-auto flex min-h-[80vh] max-w-md items-center px-4 py-16">
      <div className="w-full">
        <div className="rounded-2xl border border-zinc-200 bg-white p-8 shadow-sm">
          <div className="flex items-center gap-3">
            <span
              aria-hidden="true"
              className="flex h-11 w-11 items-center justify-center rounded-xl bg-indigo-600 text-lg font-bold text-white"
            >
              X
            </span>
            <div>
              <h1 className="text-xl font-bold tracking-tight">XploClone</h1>
              <p className="text-xs text-zinc-500">Single-owner admin · v0.1.0</p>
            </div>
          </div>
          <h2 className="mt-6 text-lg font-semibold">Owner login</h2>
          <p className="mt-1 text-sm text-zinc-600">
            Sign in with the owner password set on the server. There is no signup
            and no password reset by email — if you lose it, set a new hash in{" "}
            <code className="rounded bg-zinc-100 px-1 py-0.5 text-xs">
              XPLOCLONE_WEB_PASSWORD_HASH
            </code>{" "}
            and restart the web service.
          </p>
          <form onSubmit={submit} className="mt-6">
            <label className="block text-sm font-medium" htmlFor="password">
              Password
            </label>
            <div className="relative mt-2">
              <input
                id="password"
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
                placeholder="Enter your owner password"
                className="w-full rounded-lg border border-zinc-300 bg-white p-3 pr-20 text-sm focus:border-indigo-500"
              />
              <button
                type="button"
                onClick={() => setShowPassword((v) => !v)}
                aria-label={showPassword ? "Hide password" : "Show password"}
                aria-pressed={showPassword}
                className="absolute right-2 top-1/2 -translate-y-1/2 rounded-md px-2 py-1 text-xs font-medium text-zinc-600 hover:bg-zinc-100"
              >
                {showPassword ? "Hide" : "Show"}
              </button>
            </div>
            <button
              type="submit"
              disabled={busy || password.length === 0}
              className="mt-4 w-full rounded-lg bg-zinc-900 px-5 py-2.5 text-sm font-medium text-white hover:bg-zinc-800 disabled:cursor-not-allowed disabled:opacity-40"
            >
              {busy ? "Signing in…" : "Sign in"}
            </button>
          </form>
          {error && (
            <p role="alert" className="mt-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">
              {error}
            </p>
          )}
        </div>
        <p className="mt-4 text-center text-xs text-zinc-500">
          Mubashir Ali&apos;s voice only · English (US / British) in Phase 1
        </p>
      </div>
    </main>
  );
}
