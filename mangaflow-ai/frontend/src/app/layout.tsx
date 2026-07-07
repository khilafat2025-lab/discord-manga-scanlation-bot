import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Providers } from "@/components/layout/Providers";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: "MangaFlow AI — AI Manga & Comic Translator",
  description: "Translate manga and comics to 100+ languages with AI. Upload PDF/EPUB, get fully translated output with original artwork preserved.",
  keywords: ["manga translator", "comic translator", "AI translation", "manga OCR", "Japanese to English"],
  authors: [{ name: "MangaFlow AI" }],
  openGraph: {
    title: "MangaFlow AI",
    description: "AI-powered manga translation in 100+ languages",
    type: "website",
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: [
    { media: "(prefers-color-scheme: dark)", color: "#0a0a0f" },
    { media: "(prefers-color-scheme: light)", color: "#ffffff" },
  ],
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <body className={`${inter.variable} font-sans antialiased bg-[#0a0a0f] text-white`}>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
