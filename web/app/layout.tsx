import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "XploClone — Generate",
  description: "Single-owner voice-cloning TTS: Mubashir Ali's voice, English US/GB.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-zinc-50 text-zinc-900 antialiased">{children}</body>
    </html>
  );
}
