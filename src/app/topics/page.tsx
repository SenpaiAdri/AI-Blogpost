import Navbar from "@/components/Navbar";
import TransitionLink from "@/components/TransitionLink";
import { getTagsWithPostCounts } from "@/lib/posts";
import type { Metadata } from "next";

export const revalidate = 120;

export const metadata: Metadata = {
  title: "Topics",
  description:
    "Browse autonomous tech coverage by topic — security, cloud, AI, dev tools, and more.",
};

export default async function TopicsPage() {
  const tagRows = await getTagsWithPostCounts();

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

          {tagRows.length === 0 ? (
            <p className="text-[#6A6B70] text-sm">
              No tags yet. Run the ingest pipeline to publish posts with tags.
            </p>
          ) : (
            <ul className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {tagRows.map(({ tag, count }) => (
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
          )}

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
