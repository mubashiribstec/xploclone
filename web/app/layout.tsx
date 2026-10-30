import type { Metadata } from "next";
import Link from "next/link";
import { cookies } from "next/headers";
import "./globals.css";
import { SESSION_COOKIE, verifySession } from "@/lib/web-auth";

export const metadata: Metadata = {
  title: "XploClone — Generate",
  description: "Single-owner voice-cloning TTS: Mubashir Ali's voice, English US/GB.",
};

// Root layout: the admin nav is shown only when the owner is signed in
// (the proxy gates every page, so an unauthenticated visitor never
// reaches a page — the nav is hidden on /login by this check).
export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  const authed = verifySession(token);
  return (
    <html lang="en">
      <body className="bg-zinc-50 text-zinc-900 antialiased">
        {authed && (
          <nav className="border-b border-zinc-200 bg-white">
            <div className="mx-auto flex max-w-2xl flex-wrap items-center gap-4 px-4 py-3 text-sm">
              <span className="font-bold">XploClone</span>
              <Link href="/" className="underline">
                Generate
              </Link>
              <Link href="/voices" className="underline">
                Voices
              </Link>
              <Link href="/keys" className="underline">
                API keys
              </Link>
              <Link href="/health" className="underline">
                Health
              </Link>
              <form action="/api/auth/logout" method="post" className="ml-auto">
                <button type="submit" className="rounded border border-zinc-300 px-3 py-1">
                  Sign out
                </button>
              </form>
            </div>
          </nav>
        )}
        {children}
      </body>
    </html>
  );
}
