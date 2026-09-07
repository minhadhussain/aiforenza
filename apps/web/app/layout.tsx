import type { Metadata } from "next";
import { IBM_Plex_Sans, Space_Grotesk } from "next/font/google";

import "./globals.css";

const bodyFont = IBM_Plex_Sans({
  subsets: ["latin"],
  variable: "--font-body",
  weight: ["400", "500", "600", "700"],
});

const headingFont = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-heading",
  weight: ["500", "700"],
});

export const metadata: Metadata = {
  title: "AI Forenza | One API. Multiple frontier models.",
  description: "AI Forenza gives developers one OpenAI-compatible API for multiple frontier models with prepaid usage and simple top-ups.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className={`${bodyFont.variable} ${headingFont.variable} bg-[var(--bg)] font-[family-name:var(--font-body)] text-[var(--text)] antialiased`}>
        <div className="grain" />
        <div className="infra-glow" />
        <div className="infra-grid" />
        <div className="page-layer">{children}</div>
      </body>
    </html>
  );
}
