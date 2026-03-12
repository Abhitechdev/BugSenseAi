/** API client for BugSense AI backend. */

import type { AnalysisResponse, HistoryResponse, InputType } from "@/types";

const DEFAULT_LOCAL_API_BASE = "http://localhost:8000";
const DEFAULT_RAILWAY_API_BASE = "https://bugsenseai-production.up.railway.app";

function getApiBase(): string {
    const configured = process.env.NEXT_PUBLIC_API_URL?.trim();
    if (configured) {
        return configured.replace(/\/$/, "");
    }

    if (typeof window !== "undefined" && window.location.hostname.endsWith(".up.railway.app")) {
        return DEFAULT_RAILWAY_API_BASE;
    }

    return DEFAULT_LOCAL_API_BASE;
}

const API_BASE = getApiBase();

class ApiError extends Error {
    status: number;
    constructor(message: string, status: number) {
        super(message);
        this.status = status;
        this.name = "ApiError";
    }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
    const url = `${API_BASE}${path}`;
    const res = await fetch(url, {
        headers: { "Content-Type": "application/json", ...options?.headers },
        ...options,
    });

    if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new ApiError(
            body.detail || body.error || `Request failed with status ${res.status}`,
            res.status
        );
    }

    return res.json();
}

export const api = {
    analyzeError: (input_text: string, language_hint?: string, turnstile_token?: string | null) =>
        request<AnalysisResponse>("/api/analyze-error", {
            method: "POST",
            body: JSON.stringify({ input_text, language_hint, turnstile_token }),
        }),

    analyzeLog: (input_text: string, ci_platform?: string, turnstile_token?: string | null) =>
        request<AnalysisResponse>("/api/analyze-log", {
            method: "POST",
            body: JSON.stringify({ input_text, ci_platform, turnstile_token }),
        }),

    analyzeIssue: (input_text: string, repo_url?: string, turnstile_token?: string | null) =>
        request<AnalysisResponse>("/api/analyze-issue", {
            method: "POST",
            body: JSON.stringify({ input_text, repo_url, turnstile_token }),
        }),

    fixCode: (buggy_code: string, error_message?: string, language?: string, turnstile_token?: string | null) =>
        request<AnalysisResponse>("/api/fix-code", {
            method: "POST",
            body: JSON.stringify({ buggy_code, error_message, language, turnstile_token }),
        }),

    getHistory: (page = 1, per_page = 20, input_type?: InputType) => {
        const params = new URLSearchParams({ page: String(page), per_page: String(per_page) });
        if (input_type) params.set("input_type", input_type);
        return request<HistoryResponse>(`/api/history?${params}`);
    },

    deleteHistory: (id: string) =>
        request<{ message: string }>(`/api/history/${id}`, { method: "DELETE" }),

    clearHistory: () =>
        request<{ message: string }>("/api/history/all", { method: "DELETE" }),

    deleteCategoryHistory: (category: string) =>
        request<{ message: string }>(`/api/history/category/${category}`, { method: "DELETE" }),

    healthCheck: () => request<{ status: string }>("/health"),
};
