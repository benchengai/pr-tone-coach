import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "PR Tone Coach",
  description:
    "Check a code review comment before you post it: who the criticism targets, the phrases that may read as an attack, and a rewrite that keeps every technical point.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
