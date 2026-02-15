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
    <div className="text-center border-2 border-dashed border-[#393A41] p-5 sm:p-6 lg:p-8 hover:border-[#6A6B70] hover:bg-[#1a1a1f] transition-all duration-200">
      <p className="text-4xl sm:text-5xl md:text-6xl lg:text-7xl xl:text-8xl font-bold text-white tracking-tighter leading-none">
        {number}
        <span className="text-red-500">{suffix}</span>
      </p>
      <p className="text-[10px] sm:text-xs lg:text-sm uppercase tracking-[0.15em] text-[#6A6B70] mt-3 font-bold">
        {label}
      </p>
    </div>
  );
}