"use client";

import { useEffect, useRef, useState } from "react";

declare global {
    interface Window {
        turnstile?: {
            render: (container: HTMLElement, options: Record<string, unknown>) => string;
            reset: (widgetId?: string) => void;
            remove?: (widgetId: string) => void;
        };
    }
}

const TURNSTILE_SCRIPT_URL = "https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit";

let turnstileScriptPromise: Promise<void> | null = null;

function loadTurnstileScript(): Promise<void> {
    if (typeof window === "undefined") {
        return Promise.resolve();
    }
    if (window.turnstile) {
        return Promise.resolve();
    }
    if (!turnstileScriptPromise) {
        turnstileScriptPromise = new Promise((resolve, reject) => {
            const existing = document.querySelector<HTMLScriptElement>('script[data-turnstile-script="true"]');
            if (existing) {
                existing.addEventListener("load", () => resolve(), { once: true });
                existing.addEventListener("error", () => reject(new Error("Turnstile script failed to load.")), { once: true });
                return;
            }

            const script = document.createElement("script");
            script.src = TURNSTILE_SCRIPT_URL;
            script.async = true;
            script.defer = true;
            script.dataset.turnstileScript = "true";
            script.onload = () => resolve();
            script.onerror = () => reject(new Error("Turnstile script failed to load."));
            document.head.appendChild(script);
        });
    }
    return turnstileScriptPromise;
}

interface TurnstileWidgetProps {
    siteKey: string;
    onTokenChange: (token: string | null) => void;
    resetNonce: number;
}

export default function TurnstileWidget({ siteKey, onTokenChange, resetNonce }: TurnstileWidgetProps) {
    const containerRef = useRef<HTMLDivElement | null>(null);
    const widgetIdRef = useRef<string | null>(null);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        let cancelled = false;

        if (!siteKey) {
            onTokenChange(null);
            return undefined;
        }

        async function renderWidget() {
            try {
                await loadTurnstileScript();
                if (cancelled || !window.turnstile || !containerRef.current) {
                    return;
                }

                if (widgetIdRef.current && window.turnstile.remove) {
                    window.turnstile.remove(widgetIdRef.current);
                    widgetIdRef.current = null;
                }

                setError(null);
                widgetIdRef.current = window.turnstile.render(containerRef.current, {
                    sitekey: siteKey,
                    theme: "dark",
                    size: "flexible",
                    action: "analysis",
                    callback: (token: string) => {
                        if (!cancelled) {
                            onTokenChange(token);
                        }
                    },
                    "expired-callback": () => {
                        if (!cancelled) {
                            onTokenChange(null);
                        }
                    },
                    "error-callback": () => {
                        if (!cancelled) {
                            onTokenChange(null);
                            setError("Security challenge failed to load. Refresh and try again.");
                        }
                    },
                });
            } catch (loadError) {
                if (!cancelled) {
                    onTokenChange(null);
                    setError(loadError instanceof Error ? loadError.message : "Security challenge failed to load.");
                }
            }
        }

        void renderWidget();

        return () => {
            cancelled = true;
            if (widgetIdRef.current && window.turnstile?.remove) {
                window.turnstile.remove(widgetIdRef.current);
                widgetIdRef.current = null;
            }
        };
    }, [onTokenChange, siteKey]);

    useEffect(() => {
        if (!resetNonce || !widgetIdRef.current || !window.turnstile) {
            return;
        }
        onTokenChange(null);
        window.turnstile.reset(widgetIdRef.current);
    }, [onTokenChange, resetNonce]);

    return (
        <div className="space-y-2">
            <div ref={containerRef} />
            {error && <p className="text-sm text-red-400">{error}</p>}
        </div>
    );
}
