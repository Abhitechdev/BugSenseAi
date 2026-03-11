"use client";

import React, { useEffect, useState } from "react";
import HistoryList from "@/components/HistoryList";
import AnalysisResult from "@/components/AnalysisResult";
import type { AnalysisRecord, InputType } from "@/types";
import { api } from "@/lib/api";
import ConfirmModal from "@/components/ConfirmModal";

const FILTER_TABS: { id: string; label: string }[] = [
    { id: "all", label: "All" },
    { id: "error", label: "🐛 Errors" },
    { id: "log", label: "📋 Logs" },
    { id: "issue", label: "📝 Issues" },
    { id: "code", label: "🔧 Code" },
];

export default function HistoryPage() {
    const [items, setItems] = useState<AnalysisRecord[]>([]);
    const [total, setTotal] = useState(0);
    const [page, setPage] = useState(1);
    const [filter, setFilter] = useState("all");
    const [selected, setSelected] = useState<AnalysisRecord | null>(null);
    const [isLoading, setIsLoading] = useState(true);

    const [deleteConfirmInfo, setDeleteConfirmInfo] = useState<{ isOpen: boolean; item: AnalysisRecord | null }>({
        isOpen: false,
        item: null,
    });
    const [clearAllConfirmOpen, setClearAllConfirmOpen] = useState(false);

    const perPage = 20;

    useEffect(() => {
        setIsLoading(true);
        const inputType = filter === "all" ? undefined : (filter as InputType);

        api
            .getHistory(page, perPage, inputType)
            .then((res) => {
                setItems(res.items);
                setTotal(res.total);
            })
            .catch(() => {
                setItems([]);
                setTotal(0);
            })
            .finally(() => setIsLoading(false));
    }, [page, filter]);

    const handleDelete = async () => {
        if (!deleteConfirmInfo.item) return;
        const item = deleteConfirmInfo.item;
        setDeleteConfirmInfo({ isOpen: false, item: null });

        try {
            await api.deleteHistory(item.id);
            setItems((prev) => prev.filter((i) => i.id !== item.id));
            setTotal((prev) => Math.max(0, prev - 1));
            if (selected?.id === item.id) {
                setSelected(null);
            }
        } catch (error) {
            console.error("Failed to delete record:", error);
            alert("Failed to delete the record. Please try again.");
        }
    };

    const handleClearAll = async () => {
        setClearAllConfirmOpen(false);

        try {
            await api.clearHistory();
            setItems([]);
            setTotal(0);
            setSelected(null);
            setPage(1);
        } catch (error) {
            console.error("Failed to clear history:", error);
            alert("Failed to clear all history. Please try again.");
        }
    };

    const totalPages = Math.ceil(total / perPage);

    return (
        <div className="space-y-8">
            {/* ── Header ── */}
            <section className="animate-fade-in">
                <h1 className="text-3xl font-bold text-white">Analysis History</h1>
                <p className="mt-2 text-gray-400">
                    Browse your previous analyses. Click one to view the full result.
                </p>
            </section>

            {/* ── Filter tabs & Actions ── */}
            <div className="flex flex-wrap items-center justify-between gap-4 mb-4">
                <div className="flex flex-wrap gap-2">
                    {FILTER_TABS.map((tab) => (
                        <button
                            key={tab.id}
                            onClick={() => {
                                setFilter(tab.id);
                                setPage(1);
                                setSelected(null);
                            }}
                            className={`tab-btn ${filter === tab.id ? "active" : ""}`}
                        >
                            {tab.label}
                        </button>
                    ))}
                </div>
                {items.length > 0 && (
                    <button
                        type="button"
                        onClick={() => setClearAllConfirmOpen(true)}
                        className="px-4 py-2 text-sm font-medium text-red-400 bg-red-500/10 hover:bg-red-500/20 rounded-lg transition-colors border border-red-500/20"
                    >
                        🗑️ Clear All History
                    </button>
                )}
            </div>

            {/* ── Content ── */}
            <div className="grid gap-8 lg:grid-cols-2">
                {/* List */}
                <div className="space-y-4">
                    {isLoading ? (
                        <div className="space-y-3">
                            {[1, 2, 3, 4, 5].map((i) => (
                                <div key={i} className="glass-card shimmer h-24" />
                            ))}
                        </div>
                    ) : (
                        <>
                            <HistoryList 
                                items={items} 
                                onSelect={setSelected} 
                                onDelete={(item) => setDeleteConfirmInfo({ isOpen: true, item })} 
                            />

                            {/* Pagination */}
                            {totalPages > 1 && (
                                <div className="flex items-center justify-center gap-3 pt-4">
                                    <button
                                        onClick={() => setPage(Math.max(1, page - 1))}
                                        disabled={page <= 1}
                                        className="rounded-lg px-3 py-2 text-sm text-gray-400 transition hover:bg-white/5 disabled:opacity-30"
                                    >
                                        ← Prev
                                    </button>
                                    <span className="text-sm text-gray-500">
                                        Page {page} of {totalPages}
                                    </span>
                                    <button
                                        onClick={() => setPage(Math.min(totalPages, page + 1))}
                                        disabled={page >= totalPages}
                                        className="rounded-lg px-3 py-2 text-sm text-gray-400 transition hover:bg-white/5 disabled:opacity-30"
                                    >
                                        Next →
                                    </button>
                                </div>
                            )}
                        </>
                    )}
                </div>

                {/* Detail panel */}
                <div className="lg:sticky lg:top-24 lg:self-start">
                    {selected ? (
                        <div>
                            <div className="mb-4 flex items-center justify-between">
                                <h2 className="text-lg font-semibold text-white">Analysis Detail</h2>
                                <button
                                    onClick={() => setSelected(null)}
                                    className="rounded-lg p-2 text-gray-400 transition hover:bg-white/5 hover:text-white"
                                >
                                    ✕
                                </button>
                            </div>
                            <AnalysisResult result={selected.analysis_result} />
                        </div>
                    ) : (
                        <div className="glass-card flex flex-col items-center justify-center py-20 text-center">
                            <span className="mb-3 text-4xl">👈</span>
                            <p className="text-sm text-gray-500">
                                Select an analysis from the list to view its details
                            </p>
                        </div>
                    )}
                </div>
            </div>

            {/* ── Modals ── */}
            <ConfirmModal
                isOpen={deleteConfirmInfo.isOpen}
                title="Delete Record"
                message="Are you sure you want to delete this record?"
                onConfirm={handleDelete}
                onCancel={() => setDeleteConfirmInfo({ isOpen: false, item: null })}
            />

            <ConfirmModal
                isOpen={clearAllConfirmOpen}
                title="Clear All History"
                message="Are you sure you want to clear ALL analysis history? This cannot be undone."
                onConfirm={handleClearAll}
                onCancel={() => setClearAllConfirmOpen(false)}
            />
        </div>
    );
}
