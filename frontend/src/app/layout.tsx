import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import ErrorBoundary from "@/components/ErrorBoundary";

const inter = Inter({
    subsets: ["latin"],
    display: "swap",
    variable: "--font-sans",
});

const jetBrainsMono = JetBrains_Mono({
    subsets: ["latin"],
    display: "swap",
    variable: "--font-mono",
});

export const metadata: Metadata = {
    title: "BugSense AI — AI-Powered Error Analysis",
    description:
        "Paste your stack traces, error logs, CI/CD build logs, or GitHub issues. BugSense AI explains what went wrong and how to fix it.",
    keywords: [
        "error analysis",
        "stack trace",
        "debugging",
        "AI developer tools",
        "bug fix",
        "CI/CD",
    ],
};

export default function RootLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <html lang="en" className={`${inter.variable} ${jetBrainsMono.variable} dark`}>
            <body className="min-h-screen bg-surface-950 antialiased">
                {/* ── Background gradient orbs ── */}
                <div className="fixed inset-0 -z-10 overflow-hidden">
                    <div className="absolute -top-40 -left-40 h-[600px] w-[600px] rounded-full bg-brand-600/10 blur-[120px]" />
                    <div className="absolute top-1/2 -right-40 h-[500px] w-[500px] rounded-full bg-purple-600/10 blur-[120px]" />
                    <div className="absolute -bottom-40 left-1/3 h-[400px] w-[400px] rounded-full bg-cyan-500/8 blur-[100px]" />
                </div>

                {/* ── Navigation ── */}
                <nav className="sticky top-0 z-50 border-b border-white/5 bg-surface-950/80 backdrop-blur-xl">
                    <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
                        <a href="/" className="flex items-center gap-3 group">
                            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-brand-500 to-purple-600 shadow-lg shadow-brand-500/25 transition-transform group-hover:scale-110">
                                <svg
                                    xmlns="http://www.w3.org/2000/svg"
                                    className="h-5 w-5 text-white"
                                    viewBox="0 0 24 24"
                                    fill="none"
                                    stroke="currentColor"
                                    strokeWidth="2"
                                >
                                    <path d="M12 20h.01M8 16h.01M16 16h.01M6 12h.01M18 12h.01M12 4v4M8 8l-2-2M16 8l2-2" />
                                    <circle cx="12" cy="12" r="3" />
                                </svg>
                            </div>
                            <span className="text-xl font-bold bg-gradient-to-r from-white to-gray-400 bg-clip-text text-transparent">
                                BugSense<span className="text-brand-400"> AI</span>
                            </span>
                        </a>
                        <div className="flex items-center gap-6">
                            <a
                                href="/"
                                className="text-sm text-gray-400 transition hover:text-white"
                            >
                                Analyze
                            </a>
                            <a
                                href="/history"
                                className="text-sm text-gray-400 transition hover:text-white"
                            >
                                History
                            </a>
                            <div className="h-4 w-px bg-white/10" />
                            <a
                                href="https://github.com/Abhitechdev/BugSenseAi"
                                target="_blank"
                                rel="noreferrer"
                                className="text-sm text-gray-500 transition hover:text-white"
                            >
                                GitHub
                            </a>
                        </div>
                    </div>
                </nav>

                {/* ── Main content ── */}
                <ErrorBoundary>
                    <main className="mx-auto max-w-7xl px-6 py-8">{children}</main>
                </ErrorBoundary>

                {/* ── Footer ── */}
                <footer className="border-t border-white/5 mt-16">
                    <div className="mx-auto max-w-7xl px-6 py-8 text-center text-sm text-gray-500">
                        © {new Date().getFullYear()} BugSense AI — Built for developers, by developers.
                    </div>
                </footer>
            </body>
        </html>
    );
}
