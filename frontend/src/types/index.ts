/** Shared TypeScript types for BugSense AI frontend. */

export interface AnalysisResponse {
    language: string;
    environment: string;
    error_type: string;
    explanation: string;
    root_cause: string;
    fix: string;
    example_solution: string;
    similar_errors_found?: number;
}

export interface AnalysisRecord {
    id: string;
    input_type: InputType;
    input_text: string;
    analysis_result: AnalysisResponse;
    language_detected?: string;
    created_at: string;
}

export interface HistoryResponse {
    items: AnalysisRecord[];
    total: number;
    page: number;
    per_page: number;
}

export type InputType = "error" | "log" | "issue" | "code";

export interface TabItem {
    id: InputType;
    label: string;
    placeholder: string;
    icon: string;
    description: string;
    deleteLabel?: string;
}
