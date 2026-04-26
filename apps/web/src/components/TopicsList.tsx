"use client";

import type { TagWithCount } from "@/lib/posts";
import { useEffect, useMemo, useRef, useState } from "react";
import TransitionLink from "./TransitionLink";

type TagsResponse = {
  tags: TagWithCount[];
  hasMore: boolean;
};

type Props = {
  initialTags: TagWithCount[];
  initialHasMore?: boolean;
  pageSize?: number;
};

export default function TopicsList({
  initialTags,
  initialHasMore,
  pageSize = 50,
}: Props) {
  const [allTags, setAllTags] = useState<TagWithCount[]>(initialTags);
  const [hasMore, setHasMore] = useState<boolean>(
    initialHasMore ?? initialTags.length >= pageSize
  );
  const [query, setQuery] = useState("");
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const sentinelRef = useRef<HTMLDivElement | null>(null);

  const filteredTags = useMemo(() => {
    if (!query.trim()) return allTags;
    const lower = query.toLowerCase().trim();
    return allTags.filter(({ tag }) => tag.name.toLowerCase().includes(lower));
  }, [allTags, query]);

  useEffect(() => {
    setAllTags(initialTags);
    setHasMore(initialHasMore ?? initialTags.length >= pageSize);
  }, [initialTags, initialHasMore, pageSize]);

  useEffect(() => {
    const node = sentinelRef.current;
    if (!node || !hasMore || query.trim()) return;

    const observer = new IntersectionObserver(
      (entries) => {
        if (!entries.some((e) => e.isIntersecting) || isLoadingMore) return;

        const loadMore = async () => {
          try {
            setIsLoadingMore(true);
            const params = new URLSearchParams({
              offset: String(allTags.length),
              limit: String(pageSize),
            });
            const res = await fetch(`/api/tags?${params.toString()}`, {
              method: "GET",
              cache: "no-store",
            });
            if (!res.ok) {
              setHasMore(false);
              return;
            }
            const data = (await res.json()) as TagsResponse;
            setAllTags((prev) => {
              const seen = new Set(prev.map((t) => String(t.tag.id)));
              const next = [...prev];
              for (const t of data.tags || []) {
                if (!seen.has(String(t.tag.id))) {
                  next.push(t);
                }
              }
              return next;
            });
            setHasMore(Boolean(data.hasMore));
          } catch {
            setHasMore(false);
          } finally {
            setIsLoadingMore(false);
          }
        };

        loadMore();
      },
      { rootMargin: "100px" }
    );

    observer.observe(node);
    return () => observer.disconnect();
  }, [hasMore, isLoadingMore, allTags.length, pageSize, query]);

  if (initialTags.length === 0 && allTags.length === 0) {
    return (
      <p className="text-[#6A6B70] text-sm">
        No tags yet. Run the ingest pipeline to publish posts with tags.
      </p>
    );
  }

  return (
    <>
      <div className="mb-6">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search topics..."
          className="w-full max-w-xs px-4 py-2.5 rounded-xl border-2 border-[#393A41] border-dashed bg-[#1a1a1f] text-white placeholder-[#6A6B70]
            focus:outline-none focus:border-red-400/70 focus:bg-[#1f1f24] transition-colors text-sm"
        />
      </div>
      {filteredTags.length === 0 ? (
        <p className="text-[#6A6B70] text-sm">
          No topics match &quot;{query}&quot;.
        </p>
      ) : (
        <>
          <ul className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {filteredTags.map(({ tag, count }) => (
              <li key={String(tag.id)}>
                <TransitionLink
                  href={`/?tag=${encodeURIComponent(tag.slug)}`}
                  className="flex items-center justify-between gap-4 p-4 rounded-xl border-2 border-[#393A41] border-dashed
                    hover:border-red-400/70 hover:bg-[#1a1a1f] transition-colors group"
                >
                  <span className="font-semibold text-white group-hover:text-red-300">
                    {tag.name}
                  </span>
                  <span className="text-sm tabular-nums text-[#6A6B70] group-hover:text-[#9A9BA2]">
                    {count} post{count === 1 ? "" : "s"}
                  </span>
                </TransitionLink>
              </li>
            ))}
          </ul>
          {hasMore && !query.trim() && (
            <div ref={sentinelRef} className="mt-8 flex justify-center">
              {isLoadingMore && (
                <div className="flex items-center gap-2 text-[#6A6B70] text-sm">
                  <span className="h-4 w-4 animate-spin rounded-full border-2 border-[#393A41] border-t-red-400" />
                  Loading more...
                </div>
              )}
            </div>
          )}
        </>
      )}
    </>
  );
}