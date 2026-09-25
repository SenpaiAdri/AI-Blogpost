"use client";

type Props = {
  count?: number;
};

export default function TopicsListSkeleton({ count = 50 }: Props) {
  return (
    <div className="mb-6">
      <div className="w-full max-w-xs h-10 rounded-xl bg-surface-3 animate-pulse" />
      <ul className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-6">
        {Array.from({ length: Math.min(count, 50) }).map((_, i) => (
          <li
            key={i}
            className="flex items-center justify-between gap-4 p-4 rounded-xl border-2 border-line border-dashed bg-surface-3 animate-pulse"
          >
            <span className="h-5 w-24 rounded bg-line" />
            <span className="h-4 w-12 rounded bg-line" />
          </li>
        ))}
      </ul>
    </div>
  );
}