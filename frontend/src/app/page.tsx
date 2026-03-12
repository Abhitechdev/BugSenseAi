import HomePageClient from "@/components/HomePageClient";

export const dynamic = "force-dynamic";

export default function HomePage() {
    const turnstileSiteKey = process.env.NEXT_PUBLIC_TURNSTILE_SITE_KEY?.trim() ?? "";
    return <HomePageClient turnstileSiteKey={turnstileSiteKey} />;
}
