"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";

const LINKS = [
  { href: "/", label: "Generate" },
  { href: "/voices", label: "Voices" },
  { href: "/keys", label: "API keys" },
  { href: "/health", label: "Health" },
];

/** Sticky admin nav with an active-page highlight and a working sign-out. */
export default function SiteNav() {
  const pathname = usePathname();
  const router = useRouter();
  const [signingOut, setSigningOut] = useState(false);
  const [signOutError, setSignOutError] = useState("");

  async function signOut() {
    setSignOutError("");
    setSigningOut(true);
    try {
      const res = await fetch("/api/auth/logout", { method: "POST" });
      if (!res.ok) {
        setSignOutError("Sign-out failed — please try again.");
        return;
      }
      router.push("/login");
      router.refresh();
    } catch {
      setSignOutError("Network error — please try again.");
    } finally {
      setSigningOut(false);
    }
  }

  return (
    <header className="sticky top-0 z-40 border-b border-zinc-800 bg-zinc-900 text-white shadow-sm">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-2 gap-y-2 px-4 py-3">
        <Link href="/" className="mr-2 flex items-center gap-2" aria-label="XploClone home">
          <span
            aria-hidden="true"
            className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-600 text-sm font-bold"
          >
            X
          </span>
          <span className="text-base font-bold tracking-tight">XploClone</span>
          <span className="hidden rounded-full bg-zinc-800 px-2 py-0.5 text-[11px] font-medium text-zinc-300 sm:inline">
            v0.1.0 · Phase 1
          </span>
        </Link>
        <nav aria-label="Admin" className="flex flex-wrap items-center gap-1">
          {LINKS.map((l) => {
            const active = pathname === l.href;
            return (
              <Link
                key={l.href}
                href={l.href}
                aria-current={active ? "page" : undefined}
                className={`rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
                  active
                    ? "bg-white text-zinc-900"
                    : "text-zinc-300 hover:bg-zinc-800 hover:text-white"
                }`}
              >
                {l.label}
              </Link>
            );
          })}
        </nav>
        <div className="ml-auto flex items-center gap-2">
          {signOutError && (
            <span role="alert" className="text-xs text-red-300">
              {signOutError}
            </span>
          )}
          <button
            type="button"
            onClick={signOut}
            disabled={signingOut}
            className="rounded-lg border border-zinc-600 px-3 py-1.5 text-sm font-medium text-zinc-200 hover:bg-zinc-800 disabled:opacity-50"
          >
            {signingOut ? "Signing out…" : "Sign out"}
          </button>
        </div>
      </div>
    </header>
  );
}
