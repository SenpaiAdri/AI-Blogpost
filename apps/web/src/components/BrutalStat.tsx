/* ── Stat with bold number ── */
export default function BrutalStat({
  number,
  label,
  suffix = "",
}: {
  number: string;
  label: string;
  suffix?: string;
}) {
  return (
    <div className="text-center border-2 border-dashed border-line-strong p-5 sm:p-6 lg:p-8 hover:border-brand hover:bg-brand/5 transition-all duration-200">
      <p className="text-4xl sm:text-5xl md:text-6xl lg:text-7xl xl:text-8xl font-bold text-ink-bright tracking-tighter leading-none">
        {number}
        <span className="text-brand">{suffix}</span>
      </p>
      <p className="text-[10px] sm:text-xs lg:text-sm uppercase tracking-[0.15em] text-ink-faint mt-3 font-bold">
        {label}
      </p>
    </div>
  );
}