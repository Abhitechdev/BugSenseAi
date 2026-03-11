"use client";

import React, { useState } from "react";
import type { InputType, TabItem } from "@/types";

const TABS: TabItem[] = [
    {
        id: "error",
        label: "Error / Stack Trace",
        placeholder:
            "Paste your error message or stack trace here...\n\nExample:\nTraceback (most recent call last):\n  File \"app.py\", line 42, in handler\n    result = process_data(data)\nTypeError: cannot unpack non-iterable NoneType object",
        icon: "🐛",
        description: "Analyze stack traces and error messages",
        deleteLabel: "Delete Runtime History",
    },
    {
        id: "log",
        label: "CI/CD Logs",
        placeholder:
            "Paste your CI/CD build log here...\n\nExample:\nStep 5/8 : RUN npm run build\n---\nnpm ERR! code ELIFECYCLE\nnpm ERR! errno 1\nnpm ERR! bugsense@1.0.0 build: `next build`\nnpm ERR! Exit status 1",
        icon: "📋",
        description: "Identify failing pipeline steps",
        deleteLabel: "Delete CI/CD History",
    },
    {
        id: "issue",
        label: "GitHub Issue",
        placeholder:
            "Paste the GitHub issue text here...\n\nExample:\n## Bug Report\nAfter upgrading to v3.2, the authentication middleware\nthrows a 500 error when the JWT token has expired.\n\n### Steps to reproduce\n1. Login with valid credentials\n2. Wait for token expiry\n3. Make any API request",
        icon: "📝",
        description: "Extract error context from issues",
        deleteLabel: "Delete Issue History",
    },
    {
        id: "code",
        label: "Code Fix",
        placeholder:
            'Paste your buggy code here...\n\nExample:\ndef calculate_average(numbers):\n    total = 0\n    for n in numbers:\n        total += n\n    return total / len(numbers)  # ZeroDivisionError on empty list',
        icon: "🔧",
        description: "Generate corrected code with explanations",
        deleteLabel: "Delete Fix History",
    },
];

interface ErrorInputProps {
    onSubmit: (text: string, type: InputType) => void;
    isLoading: boolean;
    onDeleteCategory?: (type: InputType) => void;
    isDeleting?: boolean;
}

export default function ErrorInput({ onSubmit, isLoading, onDeleteCategory, isDeleting }: ErrorInputProps) {
    const [activeTab, setActiveTab] = useState<InputType>("error");
    const [inputText, setInputText] = useState("");

    const currentTab = TABS.find((t) => t.id === activeTab)!;

    const handleSubmit = () => {
        if (inputText.trim().length < 10) return;
        onSubmit(inputText, activeTab);
    };

    return (
        <div className="glass-card animate-fade-in">
            {/* ── Tab selector ── */}
            <div className="mb-6 flex flex-wrap gap-2">
                {TABS.map((tab) => (
                    <button
                        key={tab.id}
                        onClick={() => setActiveTab(tab.id)}
                        className={`tab-btn flex items-center gap-2 ${activeTab === tab.id ? "active" : ""
                            }`}
                    >
                        <span>{tab.icon}</span>
                        <span className="hidden sm:inline">{tab.label}</span>
                    </button>
                ))}
            </div>

            {/* ── Description ── */}
            <p className="mb-4 text-sm text-gray-400">{currentTab.description}</p>

            {/* ── Textarea ── */}
            <textarea
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                placeholder={currentTab.placeholder}
                rows={12}
                maxLength={50000}
                className="input-area resize-y"
                spellCheck={false}
            />

            {/* ── Actions ── */}
            <div className="mt-4 flex items-center justify-between">
                <span className="text-xs text-gray-500">
                    {inputText.length.toLocaleString()} / 50,000 characters
                </span>
                <div className="flex items-center gap-3">
                    <button
                        type="button"
                        onClick={() => setInputText("")}
                        className="rounded-lg px-4 py-2.5 text-sm text-gray-400 transition hover:bg-white/5 hover:text-white"
                    >
                        Clear
                    </button>
                    <button
                        onClick={handleSubmit}
                        disabled={isLoading || inputText.trim().length < 10}
                        className="btn-primary flex items-center gap-2"
                    >
                        {isLoading ? (
                            <>
                                <svg
                                    className="h-4 w-4 animate-spin"
                                    viewBox="0 0 24 24"
                                    fill="none"
                                >
                                    <circle
                                        className="opacity-25"
                                        cx="12"
                                        cy="12"
                                        r="10"
                                        stroke="currentColor"
                                        strokeWidth="4"
                                    />
                                    <path
                                        className="opacity-75"
                                        fill="currentColor"
                                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                                    />
                                </svg>
                                Analyzing...
                            </>
                        ) : (
                            <>
                                <svg
                                    xmlns="http://www.w3.org/2000/svg"
                                    className="h-4 w-4"
                                    viewBox="0 0 24 24"
                                    fill="none"
                                    stroke="currentColor"
                                    strokeWidth="2"
                                >
                                    <path d="M13 10V3L4 14h7v7l9-11h-7z" />
                                </svg>
                                Analyze
                            </>
                        )}
                    </button>
                    {onDeleteCategory && (
                        <button
                            type="button"
                            onClick={() => onDeleteCategory(activeTab)}
                            disabled={isLoading || isDeleting}
                            className={`rounded-xl px-6 py-3 text-sm font-semibold transition-all duration-300 ${
                                isDeleting ? "opacity-50 cursor-not-allowed bg-red-900 text-gray-300" : "bg-red-600 text-white hover:bg-red-500 hover:-translate-y-0.5 shadow-lg shadow-red-500/30"
                            }`}
                        >
                            {isDeleting ? "Deleting..." : (currentTab as any).deleteLabel || "Delete History"}
                        </button>
                    )}
                </div>
            </div>
        </div>
    );
}
