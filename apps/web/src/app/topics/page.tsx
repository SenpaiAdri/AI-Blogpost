import Navbar from "@/components/Navbar";
import TopicsList from "@/components/TopicsList";
import TopicsListSkeleton from "@/components/TopicsListSkeleton";
import TransitionLink from "@/components/TransitionLink";
import { getPaginatedTags } from "@/lib/posts";
import type { Metadata } from "next";
import { Suspense } from "react";

export const revalidate = 120;

const PAGE_SIZE = 50;

export const metadata: Metadata = {
  title: "Topics",
  description:
    "Browse autonomous tech coverage by topic — security, cloud, AI, dev tools, and more.",
};

export default async function TopicsPage() {
  return (
    <div className="min-h-screen w-full bg-[#131316] text-white">
      <Navbar />
      <div className="w-full flex justify-center">
        <main
          className="w-full max-w-4xl border-x-2 border-[#6A6B70] border-dashed min-h-screen pt-24 px-4 sm:px-8 pb-20
        md:pt-28"
        >
          <header className="max-w-2xl mb-10 space-y-3">
            <p className="text-[10px] font-bold uppercase tracking-[0.3em] text-[#6A6B70]">
              [TOPICS]
            </p>
            <h1 className="text-3xl sm:text-4xl font-bold tracking-tight">
              Browse by topic
            </h1>
            <p className="text-sm text-[#9A9BA2] leading-relaxed">
              Each tag links to posts that mention that theme. Counts reflect
              published articles only.
            </p>
          </header>

          <Suspense fallback={<TopicsListSkeleton count={PAGE_SIZE} />}>
            <TopicsListSection />
          </Suspense>

          <p className="mt-12 text-center">
            <TransitionLink
              href="/"
              className="text-sm font-bold uppercase tracking-wider text-[#6A6B70] hover:text-red-400 transition-colors"
            >
              ← Back to all posts
            </TransitionLink>
          </p>
        </main>
      </div>
    </div>
  );
}

async function TopicsListSection() {
  const { tags, hasMore } = await getPaginatedTags(0, PAGE_SIZE);

  return (
    <TopicsList initialTags={tags} initialHasMore={hasMore} pageSize={PAGE_SIZE} />
  );
}