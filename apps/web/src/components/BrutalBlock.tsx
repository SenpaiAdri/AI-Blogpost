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
      className={`border-2 border-dashed transition-[opacity,transform] duration-700 ${visible
        ? "opacity-100 translate-y-0"
        : "opacity-0 translate-y-8"
        } ${accent
          ? "border-brand bg-brand/5"
          : "border-line-strong bg-surface"
        }`}
      style={{ transitionDelay: `${delay}ms` }}
    >
      {/* Label bar */}
      <div
        className={`px-5 sm:px-6 lg:px-8 py-2.5 border-b-2 flex items-center justify-between ${accent ? "border-brand border-dashed bg-brand/10" : "border-line-strong border-dashed bg-surface-2"
          }`}
      >
        <span className="text-[10px] sm:text-xs font-bold uppercase tracking-[0.2em] text-ink-faint">
          [{label}]
        </span>
        <span className="text-[10px] text-ink-faint font-mono">●</span>
      </div>
      <div className="p-5 sm:p-7 lg:p-10">{children}</div>
    </div>
  );
}