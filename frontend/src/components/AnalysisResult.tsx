"use client";

import React from "react";
import type { AnalysisResponse } from "@/types";
import CodeBlockViewer from "./CodeBlockViewer";

interface AnalysisResultProps {
    result: AnalysisResponse;
}

const SECTIONS = [
    {
        key: "error_type" as const,
        title: "Error Type",
        icon: "🏷️",
        color: "from-red-500/20 to-orange-500/20",
        borderColor: "border-red-500/30",
    },
    {
        key: "explanation" as const,
        title: "What Happened",
        icon: "💡",
        color: "from-blue-500/20 to-cyan-500/20",
        borderColor: "border-blue-500/30",
    },
    {
        key: "root_cause" as const,
        title: "Root Cause",
        icon: "🔍",
        color: "from-amber-500/20 to-yellow-500/20",
        borderColor: "border-amber-500/30",
    },
    {
        key: "fix" as const,
        title: "How to Fix",
        icon: "✅",
        color: "from-green-500/20 to-emerald-500/20",
        borderColor: "border-green-500/30",
    },
];

export default function AnalysisResult({ result }: AnalysisResultProps) {
    return (
        <div className="space-y-4 animate-slide-up">
            {/* ── Meta badges ── */}
            <div className="flex flex-wrap gap-2 mb-6">
                {result.language && result.language.toLowerCase() !== "unknown" && (
                    <span className="inline-flex items-center gap-1.5 rounded-full bg-brand-500/15 px-3 py-1 text-xs font-medium text-brand-300 ring-1 ring-brand-500/30">
                        <span className="h-1.5 w-1.5 rounded-full bg-brand-400" />
                        {result.language}
                    </span>
                )}
                {result.environment && result.environment.toLowerCase() !== "unknown" && (
                    <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-500/15 px-3 py-1 text-xs font-medium text-emerald-300 ring-1 ring-emerald-500/30">
                        <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
                        {result.environment}
                    </span>
                )}
                {(result.similar_errors_found ?? 0) > 0 && (
                    <span className="inline-flex items-center gap-1.5 rounded-full bg-purple-500/15 px-3 py-1 text-xs font-medium text-purple-300 ring-1 ring-purple-500/30">
                        {result.similar_errors_found} similar errors found
                    </span>
                )}
            </div>

            {/* ── Sections ── */}
            {SECTIONS.map((section, idx) => (
                <div
                    key={section.key}
                    className={`glass-card border-l-4 ${section.borderColor}`}
                    style={{ animationDelay: `${idx * 100}ms` }}
                >
                    <div className="flex items-start gap-3">
                        <span className="text-xl">{section.icon}</span>
                        <div className="flex-1">
                            <h3 className="mb-2 text-sm font-semibold uppercase tracking-wider text-gray-400">
                                {section.title}
                            </h3>
                            <p className="text-gray-200 leading-relaxed whitespace-pre-wrap">
                                {result[section.key]}
                            </p>
                        </div>
                    </div>
                </div>
            ))}

            {/* ── Code example ── */}
            {result.example_solution && (
                <div className="glass-card border-l-4 border-brand-500/30">
                    <div className="flex items-start gap-3">
                        <span className="text-xl">🧩</span>
                        <div className="flex-1">
                            <h3 className="mb-3 text-sm font-semibold uppercase tracking-wider text-gray-400">
                                Example Solution
                            </h3>
                            <CodeBlockViewer code={result.example_solution} />
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
