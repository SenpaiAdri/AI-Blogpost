"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import BlogCard from "@/components/BlogCard";
import TransitionLink from "@/components/TransitionLink";
import { Post } from "@/lib/types";

type PostFeedProps = {
  initialPosts: Post[];
  activeTagSlug: string | null;
  activeTagName: string | null;
  tagQueryInvalid: boolean;
  pageSize?: number;
  initialHasMore?: boolean;
  isInitialLoading?: boolean;
};

type PostPageResponse = {
  posts: Post[];
  hasMore: boolean;
};

export function PostCardSkeleton() {
  return (
    <div className="relative block p-6 border-2 border-[#393A41] border-dashed rounded-2xl animate-pulse">
      <div className="h-8 w-2/3 bg-[#26262C] rounded-md mb-4" />
      <div className="h-4 w-1/3 bg-[#26262C] rounded mb-5" />
      <div className="space-y-2">
        <div className="h-4 w-full bg-[#26262C] rounded" />
        <div className="h-4 w-11/12 bg-[#26262C] rounded" />
        <div className="h-4 w-10/12 bg-[#26262C] rounded" />
      </div>
      <div className="mt-6 h-4 w-1/4 bg-[#26262C] rounded" />
    </div>
  );
}

export function PostFeedSkeleton({ count = 10 }: { count?: number }) {
  return (
    <div className="flex flex-col gap-6">
      {Array.from({ length: count }).map((_, i) => (
        <PostCardSkeleton key={i} />
      ))}
    </div>
  );
}

export default function PostFeed({
  initialPosts,
  activeTagSlug,
  activeTagName,
  tagQueryInvalid,
  pageSize = 10,
  initialHasMore,
  isInitialLoading: externalInitialLoading,
}: PostFeedProps) {
  const [posts, setPosts] = useState<Post[]>(initialPosts);
  const [hasMore, setHasMore] = useState<boolean>(
    initialHasMore ?? initialPosts.length >= pageSize
  );
  const [isLoadingMore, setIsLoadingMore] = useState<boolean>(false);
  const [isInitialLoading, setIsInitialLoading] = useState<boolean>(
    Boolean(externalInitialLoading)
  );
  const sentinelRef = useRef<HTMLDivElement | null>(null);

  const postsLoadedRef = useRef(false);

  const emptyPrimary = useMemo(() => {
    return activeTagSlug && !tagQueryInvalid
      ? "No published posts with this tag yet."
      : "No posts found.";
  }, [activeTagSlug, tagQueryInvalid]);

  const emptySecondary = useMemo(() => {
    return activeTagSlug && !tagQueryInvalid
      ? "Try another topic or view all posts."
      : "Check back after the next ingest run.";
  }, [activeTagSlug, tagQueryInvalid]);

  const endMessage = useMemo(() => {
    return activeTagSlug && !tagQueryInvalid
      ? "End of results for this topic."
      : "That's all for now! Check back after the next update.";
  }, [activeTagSlug, tagQueryInvalid]);

  useEffect(() => {
    setPosts(initialPosts);
    setHasMore(initialHasMore ?? initialPosts.length >= pageSize);
    setIsLoadingMore(false);
    setIsInitialLoading(Boolean(externalInitialLoading));
  }, [initialPosts, initialHasMore, pageSize, activeTagSlug, externalInitialLoading]);

  useEffect(() => {
    if (postsLoadedRef.current) return;
    if (posts.length > 0) {
      postsLoadedRef.current = true;
      setIsInitialLoading(false);
    }
  }, [posts.length]);

  useEffect(() => {
    const node = sentinelRef.current;
    if (!node || !hasMore) return;

    const observer = new IntersectionObserver(
      (entries) => {
        if (!entries.some((e) => e.isIntersecting) || isLoadingMore) return;

        const loadMore = async () => {
          try {
            setIsLoadingMore(true);
            const params = new URLSearchParams({
              offset: String(posts.length),
              limit: String(pageSize),
            });
            if (activeTagSlug && !tagQueryInvalid) {
              params.set("tag", activeTagSlug);
            }
            const res = await fetch(`/api/posts?${params.toString()}`, {
              method: "GET",
              cache: "no-store",
            });
            if (!res.ok) {
              setHasMore(false);
              return;
            }
            const data = (await res.json()) as PostPageResponse;
            setPosts((prev) => {
              const seen = new Set(prev.map((p) => p.id));
              const next = [...prev];
              for (const p of data.posts || []) {
                if (!seen.has(p.id)) {
                  next.push(p);
                }
              }
              return next;
            });
            setHasMore(Boolean(data.hasMore));
          } finally {
            setIsLoadingMore(false);
          }
        };

        void loadMore();
      },
      { root: null, rootMargin: "400px 0px", threshold: 0.01 }
    );

    observer.observe(node);
    return () => observer.disconnect();
  }, [activeTagSlug, hasMore, isLoadingMore, pageSize, posts.length, tagQueryInvalid]);

  if (isInitialLoading) {
    return <PostFeedSkeleton count={pageSize} />;
  }

  if (!posts.length) {
    return (
      <div className="text-center text-gray-500 mt-16 space-y-2">
        <p>{emptyPrimary}</p>
        <p className="text-sm text-[#6A6B70]">{emptySecondary}</p>
        {activeTagSlug && !tagQueryInvalid && (
          <p className="pt-4">
            <TransitionLink
              href="/"
              className="text-sm font-bold text-red-400 hover:underline uppercase tracking-wide"
            >
              Clear filter
            </TransitionLink>
          </p>
        )}
      </div>
    );
  }

  return (
    <>
      {activeTagName && !tagQueryInvalid && (
        <div className="flex flex-wrap items-baseline justify-between gap-2 px-1">
          <h2 className="text-lg font-bold text-white">
            <span className="text-[#6A6B70] font-semibold text-sm uppercase tracking-wider mr-2">
              Topic
            </span>
            {activeTagName}
          </h2>
          <p className="text-sm text-[#6A6B70]">
            {posts.length}+ post{posts.length === 1 ? "" : "s"}
          </p>
        </div>
      )}

      {posts.map((post) => (
        <BlogCard key={post.id} post={post} />
      ))}

      {isLoadingMore && (
        <>
          <PostCardSkeleton />
          <PostCardSkeleton />
          <PostCardSkeleton />
        </>
      )}

      <div ref={sentinelRef} className="h-2 w-full" aria-hidden />

      {!hasMore && (
        <p className="text-center text-sm text-gray-400 px-10 sm:pt-10 sm:pb-6">{endMessage}</p>
      )}
    </>
  );
}
