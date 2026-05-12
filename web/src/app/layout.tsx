import type { Metadata } from "next";
import { Geist } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const geist = Geist({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "SPY vs QQQ — Group 6700",
  description: "ETF Asset Allocator — CSc 46000",
};

const nav = [
  { href: "/",               label: "Overview"       },
  { href: "/allocator",      label: "Allocator"      },
  { href: "/risk",           label: "Risk Profile"   },
  { href: "/ab-comparison",  label: "A/B Test"       },
  { href: "/ml-predictions", label: "ML Predictions" },
];

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={`${geist.className} min-h-screen bg-gray-950 text-gray-100`}>
        <header className="border-b border-gray-800 px-8 py-4 flex items-center justify-between sticky top-0 bg-gray-950/90 backdrop-blur z-50">
          <span className="font-bold text-lg tracking-tight">
            SPY <span className="text-blue-400">vs</span> QQQ
          </span>
          <nav className="flex gap-8 text-sm">
            {nav.map((n) => (
              <Link
                key={n.href}
                href={n.href}
                className="text-gray-400 hover:text-white transition-colors"
              >
                {n.label}
              </Link>
            ))}
          </nav>
        </header>
        <main className="px-8 py-8 max-w-7xl mx-auto">{children}</main>
      </body>
    </html>
  );
}
