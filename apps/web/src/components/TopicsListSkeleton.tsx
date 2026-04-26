"use client";

type Props = {
  count?: number;
};

export default function TopicsListSkeleton({ count = 50 }: Props) {
  return (
    <div className="mb-6">
      <div className="w-full max-w-xs h-10 rounded-xl bg-[#26262C] animate-pulse" />
      <ul className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-6">
        {Array.from({ length: Math.min(count, 50) }).map((_, i) => (
          <li
            key={i}
            className="flex items-center justify-between gap-4 p-4 rounded-xl border-2 border-[#393A41] border-dashed bg-[#26262C] animate-pulse"
          >
            <span className="h-5 w-24 rounded bg-[#393A41]" />
            <span className="h-4 w-12 rounded bg-[#393A41]" />
          </li>
        ))}
      </ul>
    </div>
  );
}