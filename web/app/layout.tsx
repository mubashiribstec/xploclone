import type { Metadata } from "next";
import { cookies } from "next/headers";
import "./globals.css";
import SiteNav from "@/components/SiteNav";
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
      <body className="min-h-screen bg-zinc-50 text-zinc-900 antialiased">
        {authed && <SiteNav />}
        <div className="min-h-[calc(100vh-220px)]">{children}</div>
        {authed && (
          <footer className="border-t border-zinc-200 bg-white">
            <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-2 px-4 py-4 text-xs text-zinc-500">
              <span>
                XploClone v0.1.0 · Phase 1 English MVP · Chatterbox Turbo · single-owner admin
              </span>
              <span>Mubashir Ali&apos;s voice only — no other voice can be added here.</span>
            </div>
          </footer>
        )}
      </body>
    </html>
  );
}
