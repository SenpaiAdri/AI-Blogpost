import { useEffect, useRef, useState } from "react";

/* ── Intersection observer hook for scroll-triggered animations ── */
function useReveal() {
  const ref = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setVisible(true);
          observer.disconnect();
        }
      },
      { threshold: 0.15 }
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  return { ref, visible };
}
/* ── Brutalist section block ── */
export default function BrutalBlock({
  label,
  children,
  accent = false,
  delay = 0,
}: {
  label: string;
  children: React.ReactNode;
  accent?: boolean;
  delay?: number;
}) {
  const { ref, visible } = useReveal();
  return (
    <div
      ref={ref}
      className={`border-2 border-dashed transition-all duration-700 ${visible
        ? "opacity-100 translate-y-0"
        : "opacity-0 translate-y-8"
        } ${accent
          ? "border-red-400 bg-red-400/5"
          : "border-[#6A6B70] bg-[#131316]"
        }`}
      style={{ transitionDelay: `${delay}ms` }}
    >
      {/* Label bar */}
      <div
        className={`px-5 sm:px-6 lg:px-8 py-2.5 border-b-2 flex items-center justify-between ${accent ? "border-red-400 border-dashed bg-red-500/10" : "border-[#6A6B70] border-dashed bg-[#1a1a1f]"
          }`}
      >
        <span className="text-[10px] sm:text-xs font-bold uppercase tracking-[0.2em] text-[#6A6B70]">
          [{label}]
        </span>
        <span className="text-[10px] text-[#6A6B70] font-mono">●</span>
      </div>
      <div className="p-5 sm:p-7 lg:p-10">{children}</div>
    </div>
  );
}