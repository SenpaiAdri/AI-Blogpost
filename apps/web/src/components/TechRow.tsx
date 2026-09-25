/* ── Tech row ── */
export default function TechRow({
  name,
  role,
  version,
}: {
  name: string;
  role: string;
  version: string;
}) {
  return (
    <div className="flex items-center justify-between py-4 border-b border-dashed border-line last:border-b-0 group hover:bg-surface-3 -mx-5 sm:-mx-7 lg:-mx-10 px-5 sm:px-7 lg:px-10 transition-colors">
      <div className="flex items-baseline gap-4">
        <span className="text-sm sm:text-base lg:text-lg font-bold text-ink-bright group-hover:text-brand transition-colors">
          {name}
        </span>
        <span className="text-xs sm:text-sm text-ink-faint font-mono">{version}</span>
      </div>
      <span className="text-xs sm:text-sm text-ink-faint group-hover:text-brand transition-colors uppercase tracking-wider">{role}</span>
    </div>
  );
}