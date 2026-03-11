"use client";

import React from "react";
import type { AnalysisRecord } from "@/types";

const TYPE_BADGES: Record<string, { icon: string; label: string; color: string }> = {
    error: { icon: "🐛", label: "Error", color: "bg-red-500/15 text-red-300 ring-red-500/30" },
    log: { icon: "📋", label: "CI/CD Log", color: "bg-amber-500/15 text-amber-300 ring-amber-500/30" },
    issue: { icon: "📝", label: "GitHub Issue", color: "bg-blue-500/15 text-blue-300 ring-blue-500/30" },
    code: { icon: "🔧", label: "Code Fix", color: "bg-green-500/15 text-green-300 ring-green-500/30" },
};

interface HistoryListProps {
    items: AnalysisRecord[];
    onSelect: (item: AnalysisRecord) => void;
    onDelete: (item: AnalysisRecord) => void;
}

export default function HistoryList({ items, onSelect, onDelete }: HistoryListProps) {
    if (items.length === 0) {
        return (
            <div className="glass-card flex flex-col items-center justify-center py-16 text-center">
                <span className="mb-4 text-5xl">📭</span>
                <h3 className="mb-2 text-lg font-semibold text-gray-300">No analyses yet</h3>
                <p className="text-sm text-gray-500 max-w-sm">
                    Paste an error, log, or issue on the home page to get started. Your analysis history will appear here.
                </p>
            </div>
        );
    }

    return (
        <div className="space-y-3">
            {items.map((item, idx) => {
                const badge = TYPE_BADGES[item.input_type] || TYPE_BADGES.error;
                const date = new Date(item.created_at);

                return (
                    <div
                        key={item.id}
                        onClick={() => onSelect(item)}
                        role="button"
                        tabIndex={0}
                        onKeyDown={(e) => { if (e.key === 'Enter') onSelect(item); }}
                        className="glass-card w-full text-left transition-all duration-200 hover:border-brand-500/30 hover:bg-white/[0.07] group animate-slide-up cursor-pointer"
                        style={{ animationDelay: `${idx * 50}ms` }}
                    >
                        <div className="flex items-start justify-between gap-4">
                            <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-2 mb-2">
                                    <span
                                        className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ${badge.color}`}
                                    >
                                        {badge.icon} {badge.label}
                                    </span>
                                    {item.language_detected && (
                                        <span className="text-xs text-gray-500">{item.language_detected}</span>
                                    )}
                                </div>
                                <p className="text-sm text-gray-300 line-clamp-2 font-mono">
                                    {item.input_text}
                                </p>
                                <p className="mt-2 text-xs text-gray-500">
                                    {item.analysis_result?.error_type}
                                </p>
                            </div>
                            <div className="flex flex-col items-end gap-2 shrink-0">
                                <span className="text-xs text-gray-500">
                                    {date.toLocaleDateString()} {date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                                </span>
                                <div className="flex items-center gap-2 mt-2">
                                    <button
                                        type="button"
                                        onClick={(e) => {
                                            e.stopPropagation();
                                            onDelete(item);
                                        }}
                                        className="p-1.5 rounded-md text-gray-500 hover:bg-red-500/20 hover:text-red-400 transition"
                                        title="Delete record"
                                    >
                                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                            <path d="M3 6h18"></path>
                                            <path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"></path>
                                            <path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"></path>
                                        </svg>
                                    </button>
                                    <svg
                                        xmlns="http://www.w3.org/2000/svg"
                                        className="h-4 w-4 text-gray-600 transition group-hover:text-brand-400 group-hover:translate-x-1"
                                        viewBox="0 0 24 24"
                                        fill="none"
                                        stroke="currentColor"
                                        strokeWidth="2"
                                    >
                                        <path d="M9 18l6-6-6-6" />
                                    </svg>
                                </div>
                            </div>
                        </div>
                    </div>
                );
            })}
        </div>
    );
}
