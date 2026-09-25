/* ── Marquee component with dashed stroke text ── */
export default function Marquee({ text, reverse = false }: { text: string; reverse?: boolean }) {
    return (
        <div className="overflow-hidden border-y-2 border-line-strong border-dashed py-3 sm:py-4 select-none">
            <div
                className={`flex whitespace-nowrap items-center ${reverse ? "animate-marquee-reverse" : "animate-marquee"}`}
            >
                {[...Array(6)].map((_, i) => (
                    <span key={i} className="flex items-center mr-8 sm:mr-12">
                        <h1 className="text-8xl font-bold">
                            <span
                                className="block text-transparent"
                                style={{ WebkitTextStroke: "2px var(--marquee-stroke)" }}
                            >
                                {text}
                            </span>
                        </h1>
                    </span>
                ))}
            </div>
        </div>
    );
}
