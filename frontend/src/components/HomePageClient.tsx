"use client";

import React, { useState } from "react";

import AnalysisResult from "@/components/AnalysisResult";
import ConfirmModal from "@/components/ConfirmModal";
import ErrorInput from "@/components/ErrorInput";
import { api } from "@/lib/api";
import type { AnalysisResponse, InputType } from "@/types";

interface HomePageClientProps {
    turnstileSiteKey: string;
}

export default function HomePageClient({ turnstileSiteKey }: HomePageClientProps) {
    const [result, setResult] = useState<AnalysisResponse | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [isDeleting, setIsDeleting] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const [deleteConfirmInfo, setDeleteConfirmInfo] = useState<{ isOpen: boolean; type: InputType | null }>({
        isOpen: false,
        type: null,
    });

    const confirmDeleteCategory = (type: InputType) => {
        setDeleteConfirmInfo({ isOpen: true, type });
    };

    const handleDeleteCategoryHistory = async () => {
        if (!deleteConfirmInfo.type) return;
        const type = deleteConfirmInfo.type;
        setDeleteConfirmInfo({ isOpen: false, type: null });

        const categoryMap: Record<InputType, string> = {
            error: "runtime",
            log: "cicd",
            issue: "github",
            code: "codefix",
        };
        const endpointCategory = categoryMap[type];

        setIsDeleting(true);
        try {
            await api.deleteCategoryHistory(endpointCategory);
            setResult(null);
            alert("History successfully deleted.");
        } catch {
            alert("Failed to delete history.");
        } finally {
            setIsDeleting(false);
        }
    };

    const handleAnalyze = async (text: string, type: InputType, turnstileToken: string | null) => {
        setIsLoading(true);
        setError(null);
        setResult(null);

        try {
            let response: AnalysisResponse;

            switch (type) {
                case "error":
                    response = await api.analyzeError(text, undefined, turnstileToken);
                    break;
                case "log":
                    response = await api.analyzeLog(text, undefined, turnstileToken);
                    break;
                case "issue":
                    response = await api.analyzeIssue(text, undefined, turnstileToken);
                    break;
                case "code":
                    response = await api.fixCode(text, undefined, undefined, turnstileToken);
                    break;
                default:
                    throw new Error("Unknown analysis type");
            }

            setResult(response);
        } catch (err: unknown) {
            const message =
                err instanceof Error ? err.message : "Failed to analyze. Please try again.";
            setError(message);
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="space-y-10">
            <section className="text-center pt-8 pb-4 animate-fade-in">
                <h1 className="text-4xl sm:text-5xl font-extrabold leading-tight">
                    <span className="bg-gradient-to-r from-white via-gray-200 to-gray-400 bg-clip-text text-transparent">
                        Debug Smarter with
                    </span>
                    <br />
                    <span className="bg-gradient-to-r from-brand-400 via-purple-400 to-pink-400 bg-clip-text text-transparent">
                        AI-Powered Analysis
                    </span>
                </h1>
                <p className="mx-auto mt-4 max-w-2xl text-lg text-gray-400">
                    Paste your stack traces, error logs, CI/CD failures, or buggy code. BugSense AI
                    explains what went wrong, why, and how to fix it — in seconds.
                </p>

                <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
                    {[
                        { emoji: "⚡", text: "Instant Analysis" },
                        { emoji: "🧠", text: "AI-Powered" },
                        { emoji: "🔍", text: "Root Cause Detection" },
                        { emoji: "🩹", text: "Fix Suggestions" },
                    ].map((f) => (
                        <span
                            key={f.text}
                            className="inline-flex items-center gap-1.5 rounded-full bg-white/5 px-3 py-1.5 text-sm text-gray-400 ring-1 ring-white/10"
                        >
                            {f.emoji} {f.text}
                        </span>
                    ))}
                </div>
            </section>

            <ErrorInput
                onSubmit={handleAnalyze}
                isLoading={isLoading}
                onDeleteCategory={confirmDeleteCategory}
                isDeleting={isDeleting}
                turnstileSiteKey={turnstileSiteKey}
            />

            {error && (
                <div className="glass-card border-l-4 border-red-500/50 animate-slide-up">
                    <div className="flex items-center gap-3">
                        <span className="text-xl">❌</span>
                        <div>
                            <h3 className="text-sm font-semibold text-red-400">Analysis Failed</h3>
                            <p className="mt-1 text-sm text-gray-400">{error}</p>
                        </div>
                    </div>
                </div>
            )}

            {isLoading && (
                <div className="space-y-4 animate-fade-in">
                    {[1, 2, 3, 4].map((i) => (
                        <div
                            key={i}
                            className="glass-card shimmer"
                            style={{ animationDelay: `${i * 200}ms` }}
                        >
                            <div className="h-4 w-1/4 rounded bg-white/5 mb-3" />
                            <div className="h-3 w-full rounded bg-white/5 mb-2" />
                            <div className="h-3 w-3/4 rounded bg-white/5" />
                        </div>
                    ))}
                </div>
            )}

            {result && !isLoading && (
                <section>
                    <h2 className="mb-6 text-xl font-bold text-white flex items-center gap-2">
                        <svg
                            xmlns="http://www.w3.org/2000/svg"
                            className="h-5 w-5 text-brand-400"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="2"
                        >
                            <path d="M9 12l2 2 4-4" />
                            <circle cx="12" cy="12" r="10" />
                        </svg>
                        Analysis Complete
                    </h2>
                    <AnalysisResult result={result} />
                </section>
            )}

            <ConfirmModal
                isOpen={deleteConfirmInfo.isOpen}
                title="Delete Category History"
                message="Are you sure you want to delete all history for this category? This action cannot be undone."
                onConfirm={handleDeleteCategoryHistory}
                onCancel={() => setDeleteConfirmInfo({ isOpen: false, type: null })}
            />
        </div>
    );
}
