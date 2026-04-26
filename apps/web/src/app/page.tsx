import Navbar from "@/components/Navbar";
import TopicFilterBar from "@/components/TopicFilterBar";
import PostFeed, { PostFeedSkeleton } from "@/components/PostFeed";
import BackToTopButton from "@/components/BackToTopButton";
import {
  getPaginatedPosts,
  getTagBySlug,
  getTagsWithPostCounts,
} from "@/lib/posts";
import type { Metadata } from "next";
import { Suspense } from "react";

export const revalidate = 120;

const PAGE_SIZE = 10;

export async function generateMetadata({
  searchParams,
}: {
  searchParams: Promise<{ tag?: string }>;
}): Promise<Metadata> {
  const { tag } = await searchParams;
  if (!tag?.trim()) {
    return {
      title: "AI Blogpost",
      description:
        "Autonomous tech blog — AI, security, cloud, and developer news distilled into readable posts.",
    };
  }
  const row = await getTagBySlug(tag);
  if (!row) {
    return { title: "AI Blogpost" };
  }
  return {
    title: `${row.name} · AI Blogpost`,
    description: `Posts tagged ${row.name} — tech news and analysis.`,
  };
}

export default async function Home({
  searchParams,
}: {
  searchParams: Promise<{ tag?: string }>;
}) {
  const { tag: tagParam } = await searchParams;
  const rawTag = tagParam?.trim() || "";

  return (
    <div className="min-h-screen w-full bg-[#131316] text-white">
      <Navbar />

      <div className="w-full flex justify-center">
        <main
          className="w-full max-w-4xl sm:border-x-2 sm:border-[#6A6B70] sm:border-dashed min-h-screen pt-19 px-4 pb-10 
        sm:pb-20 sm:pt-21
        md:px-8 md:pt-24"
        >
          <div className="w-full space-y-6">
            <Suspense fallback={<TopicFilterBarSkeleton />}>
              <TopicFilterBarSection rawTag={rawTag} />
            </Suspense>
            <Suspense key={rawTag || "all"} fallback={<PostFeedSkeleton count={PAGE_SIZE} />}>
              <PostFeedSection rawTag={rawTag} />
            </Suspense>
          </div>
        </main>
      </div>
      <BackToTopButton />
    </div>
  );
}

function TopicFilterBarSkeleton() {
  return (
    <div className="space-y-3 pb-2 animate-pulse">
      <div className="flex flex-wrap items-center gap-2">
        <span className="h-3 w-14 rounded bg-[#26262C]" />
        {Array.from({ length: 5 }).map((_, i) => (
          <span key={i} className="h-7 w-20 rounded-full bg-[#26262C]" />
        ))}
      </div>
    </div>
  );
}

async function TopicFilterBarSection({ rawTag }: { rawTag: string }) {
  const [tagRows, activeTag] = await Promise.all([
    getTagsWithPostCounts(),
    rawTag ? getTagBySlug(rawTag) : Promise.resolve(null),
  ]);
  const tagQueryInvalid = Boolean(rawTag && !activeTag);

  return (
    <TopicFilterBar
      tags={tagRows}
      activeSlug={activeTag?.slug ?? null}
      tagQueryInvalid={tagQueryInvalid}
    />
  );
}

async function PostFeedSection({ rawTag }: { rawTag: string }) {
  const activeTag = rawTag ? await getTagBySlug(rawTag) : null;
  const tagQueryInvalid = Boolean(rawTag && !activeTag);
  const effectiveTagSlug = activeTag?.slug ?? null;
  const initialPage = await getPaginatedPosts(
    0,
    PAGE_SIZE,
    tagQueryInvalid ? undefined : effectiveTagSlug ?? undefined
  );

  return (
    <PostFeed
      initialPosts={initialPage.posts}
      initialHasMore={initialPage.hasMore}
      activeTagSlug={effectiveTagSlug}
      activeTagName={activeTag?.name ?? null}
      tagQueryInvalid={tagQueryInvalid}
      pageSize={PAGE_SIZE}
    />
  );
}
