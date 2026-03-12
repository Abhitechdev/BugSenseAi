/** @type {import('tailwindcss').Config} */
module.exports = {
    content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
    theme: {
        extend: {
            colors: {
                brand: {
                    50: "#f0f4ff",
                    100: "#dbe4ff",
                    200: "#bac8ff",
                    300: "#91a7ff",
                    400: "#748ffc",
                    500: "#5c7cfa",
                    600: "#4c6ef5",
                    700: "#4263eb",
                    800: "#3b5bdb",
                    900: "#364fc7",
                },
                surface: {
                    50: "#f8f9fa",
                    100: "#f1f3f5",
                    200: "#e9ecef",
                    300: "#dee2e6",
                    700: "#495057",
                    800: "#343a40",
                    900: "#212529",
                    950: "#0d1117",
                },
                accent: {
                    green: "#40c057",
                    red: "#fa5252",
                    amber: "#fab005",
                    cyan: "#15aabf",
                },
            },
            fontFamily: {
                sans: ["var(--font-sans)", "ui-sans-serif", "system-ui", "sans-serif"],
                mono: ["var(--font-mono)", "Fira Code", "monospace"],
            },
            animation: {
                "fade-in": "fadeIn 0.5s ease-out",
                "slide-up": "slideUp 0.4s ease-out",
                "pulse-glow": "pulseGlow 2s ease-in-out infinite",
                "shimmer": "shimmer 2s linear infinite",
            },
            keyframes: {
                fadeIn: {
                    "0%": { opacity: "0" },
                    "100%": { opacity: "1" },
                },
                slideUp: {
                    "0%": { opacity: "0", transform: "translateY(20px)" },
                    "100%": { opacity: "1", transform: "translateY(0)" },
                },
                pulseGlow: {
                    "0%, 100%": { boxShadow: "0 0 20px rgba(92,124,250,0.3)" },
                    "50%": { boxShadow: "0 0 40px rgba(92,124,250,0.6)" },
                },
                shimmer: {
                    "0%": { backgroundPosition: "-200% 0" },
                    "100%": { backgroundPosition: "200% 0" },
                },
            },
            backgroundImage: {
                "gradient-radial": "radial-gradient(var(--tw-gradient-stops))",
            },
        },
    },
    plugins: [],
};
