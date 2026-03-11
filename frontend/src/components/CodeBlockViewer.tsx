"use client";

import React, { useState } from "react";

interface CodeBlockViewerProps {
    code: string;
    language?: string;
}

export default function CodeBlockViewer({ code }: CodeBlockViewerProps) {
    const [copied, setCopied] = useState(false);

    // Extract code from markdown code fences if present
    let displayCode = code;
    const fenceMatch = code.match(/```[\w]*\n?([\s\S]*?)```/);
    if (fenceMatch) {
        displayCode = fenceMatch[1].trim();
    }

    const handleCopy = async () => {
        try {
            await navigator.clipboard.writeText(displayCode);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        } catch {
            // fallback
            const textarea = document.createElement("textarea");
            textarea.value = displayCode;
            document.body.appendChild(textarea);
            textarea.select();
            document.execCommand("copy");
            document.body.removeChild(textarea);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        }
    };

    const lines = displayCode.split("\n");

    return (
        <div className="group relative rounded-xl border border-white/10 bg-[#0d1117] overflow-hidden">
            {/* ── Header bar ── */}
            <div className="flex items-center justify-between border-b border-white/5 bg-white/3 px-4 py-2">
                <div className="flex items-center gap-2">
                    <div className="h-3 w-3 rounded-full bg-red-500/60" />
                    <div className="h-3 w-3 rounded-full bg-yellow-500/60" />
                    <div className="h-3 w-3 rounded-full bg-green-500/60" />
                </div>
                <button
                    onClick={handleCopy}
                    className="flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs text-gray-400 transition hover:bg-white/10 hover:text-white"
                >
                    {copied ? (
                        <>
                            <svg
                                xmlns="http://www.w3.org/2000/svg"
                                className="h-3.5 w-3.5 text-green-400"
                                viewBox="0 0 24 24"
                                fill="none"
                                stroke="currentColor"
                                strokeWidth="2"
                            >
                                <polyline points="20 6 9 17 4 12" />
                            </svg>
                            Copied!
                        </>
                    ) : (
                        <>
                            <svg
                                xmlns="http://www.w3.org/2000/svg"
                                className="h-3.5 w-3.5"
                                viewBox="0 0 24 24"
                                fill="none"
                                stroke="currentColor"
                                strokeWidth="2"
                            >
                                <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                                <path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1" />
                            </svg>
                            Copy
                        </>
                    )}
                </button>
            </div>

            {/* ── Code block ── */}
            <div className="overflow-x-auto">
                <pre className="p-4 text-sm leading-6">
                    <code>
                        {lines.map((line, i) => (
                            <div key={i} className="flex">
                                <span className="mr-4 inline-block w-8 select-none text-right text-gray-600 text-xs leading-6">
                                    {i + 1}
                                </span>
                                <span className="text-gray-200">{line}</span>
                            </div>
                        ))}
                    </code>
                </pre>
            </div>
        </div>
    );
}
