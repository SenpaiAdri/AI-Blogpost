export default function BlogPostSkeleton() {
  return (
    <div className="max-w-3xl mx-auto space-y-5 animate-pulse" aria-hidden="true">
      {/* Title + meta header */}
      <header className="space-y-4">
        <div className="space-y-3">
          <div className="h-9 w-11/12 rounded-md bg-surface-3 sm:h-11" />
          <div className="h-9 w-2/3 rounded-md bg-surface-3 sm:h-11" />
        </div>
        <div className="flex flex-wrap gap-4 items-center justify-between">
          <div className="flex gap-2">
            <span className="h-6 w-16 rounded-full bg-surface-3" />
            <span className="h-6 w-20 rounded-full bg-surface-3" />
            <span className="h-6 w-14 rounded-full bg-surface-3" />
          </div>
          <span className="h-4 w-24 rounded bg-surface-3" />
        </div>
      </header>

      {/* TL;DR block */}
      <div className="px-4 space-y-2">
        <div className="h-4 w-12 rounded bg-surface-3" />
        <div className="h-4 w-full rounded bg-surface-3" />
        <div className="h-4 w-11/12 rounded bg-surface-3" />
        <div className="h-4 w-10/12 rounded bg-surface-3" />
      </div>

      {/* Body content */}
      <div className="space-y-3 pt-2">
        <div className="h-4 w-full rounded bg-surface-3" />
        <div className="h-4 w-full rounded bg-surface-3" />
        <div className="h-4 w-11/12 rounded bg-surface-3" />
        <div className="h-4 w-full rounded bg-surface-3" />
        <div className="h-4 w-10/12 rounded bg-surface-3" />
        <div className="h-4 w-full rounded bg-surface-3" />
        <div className="h-4 w-9/12 rounded bg-surface-3" />
      </div>

      {/* Sources */}
      <div className="pt-8 mt-12 space-y-3">
        <div className="h-4 w-20 rounded bg-surface-3" />
        <div className="flex flex-wrap gap-3">
          <span className="h-8 w-28 rounded-4xl bg-surface-3" />
          <span className="h-8 w-32 rounded-4xl bg-surface-3" />
        </div>
      </div>
    </div>
  );
}
