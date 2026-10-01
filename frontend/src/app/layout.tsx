import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import "./globals.css";
import { Providers } from "./providers";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "FinQuery",
  description: "AI accounts-payable copilot: extract, validate and query invoices",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">
        <header className="border-b border-line">
          <div className="mx-auto flex h-14 w-full max-w-5xl items-center px-4">
            <Link href="/" className="font-semibold tracking-tight">
              FinQuery
            </Link>
            <span className="ml-3 text-sm text-muted">Invoice inbox</span>
          </div>
        </header>
        <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-8">
          <Providers>{children}</Providers>
        </main>
      </body>
    </html>
  );
}
