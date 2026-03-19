"use client";

import React, { Component, ErrorInfo, ReactNode } from "react";

interface Props {
    children: ReactNode;
}

interface State {
    hasError: boolean;
    error?: Error;
    errorInfo?: ErrorInfo;
}

class ErrorBoundary extends Component<Props, State> {
    constructor(props: Props) {
        super(props);
        this.state = { hasError: false };
    }

    static getDerivedStateFromError(error: Error): State {
        return { hasError: true, error };
    }

    componentDidCatch(error: Error, errorInfo: ErrorInfo) {
        this.setState({
            error,
            errorInfo
        });
        
        // Log error to console in development
        if (process.env.NODE_ENV === "development") {
            console.error("ErrorBoundary caught an error:", error, errorInfo);
        }
        
        // In production, you might want to send this to an error reporting service
        if (process.env.NODE_ENV === "production") {
            // Send to error reporting service (e.g., Sentry, LogRocket, etc.)
            console.error("Production error:", error.message);
        }
    }

    render() {
        if (this.state.hasError) {
            return (
                <div className="min-h-screen flex items-center justify-center bg-surface-950">
                    <div className="max-w-md w-full mx-auto p-8 text-center">
                        <div className="mb-6">
                            <div className="inline-flex items-center justify-center w-16 h-16 bg-red-500/10 border border-red-500/30 rounded-full mb-4">
                                <svg
                                    xmlns="http://www.w3.org/2000/svg"
                                    className="h-8 w-8 text-red-400"
                                    viewBox="0 0 24 24"
                                    fill="none"
                                    stroke="currentColor"
                                    strokeWidth="2"
                                >
                                    <circle cx="12" cy="12" r="10" />
                                    <line x1="12" y1="8" x2="12" y2="12" />
                                    <line x1="12" y1="16" x2="12.01" y2="16" />
                                </svg>
                            </div>
                            <h1 className="text-2xl font-bold text-white mb-2">
                                Something went wrong
                            </h1>
                            <p className="text-gray-400">
                                We're sorry, but an unexpected error occurred. Please try refreshing the page or contact support if the problem persists.
                            </p>
                        </div>
                        
                        <div className="space-y-3">
                            <button
                                onClick={() => window.location.reload()}
                                className="w-full bg-gradient-to-r from-brand-500 to-purple-600 text-white py-3 px-4 rounded-lg font-medium hover:from-brand-600 hover:to-purple-700 transition-all duration-200 shadow-lg shadow-brand-500/25"
                            >
                                Refresh Page
                            </button>
                            <button
                                onClick={() => this.setState({ hasError: false })}
                                className="w-full bg-white/5 border border-white/10 text-gray-300 py-3 px-4 rounded-lg font-medium hover:bg-white/10 transition-all duration-200"
                            >
                                Try Again
                            </button>
                        </div>
                        
                        {process.env.NODE_ENV === "development" && this.state.error && (
                            <details className="mt-6 text-left">
                                <summary className="cursor-pointer text-sm text-gray-500 hover:text-gray-300">
                                    Error Details (Development)
                                </summary>
                                <div className="mt-2 p-3 bg-red-500/10 border border-red-500/20 rounded-lg">
                                    <p className="text-red-400 font-mono text-sm">{this.state.error.toString()}</p>
                                    {this.state.errorInfo && (
                                        <pre className="mt-2 text-xs text-gray-400 font-mono overflow-auto">
                                            {this.state.errorInfo.componentStack}
                                        </pre>
                                    )}
                                </div>
                            </details>
                        )}
                    </div>
                </div>
            );
        }

        return this.props.children;
    }
}

export default ErrorBoundary;
