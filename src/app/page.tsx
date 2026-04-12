import BlogCard from "@/components/BlogCard";
import Navbar from "@/components/Navbar";
import TopicFilterBar from "@/components/TopicFilterBar";
import TransitionLink from "@/components/TransitionLink";
import {
  aggregateTagsWithCounts,
  getPosts,
  getTagBySlug,
} from "@/lib/posts";
import { Post } from "@/lib/types";
import type { Metadata } from "next";

export const revalidate = 120;

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

  const allPosts = await getPosts();
  const tagRows = aggregateTagsWithCounts(allPosts);

  const activeTag = rawTag ? await getTagBySlug(rawTag) : null;
  let posts: Post[];
  let tagQueryInvalid = false;

  if (rawTag) {
    if (activeTag) {
      posts = allPosts.filter((p) =>
        p.tags?.some((t) => t.slug === activeTag.slug)
      );
    } else {
      tagQueryInvalid = true;
      posts = allPosts;
    }
  } else {
    posts = allPosts;
  }

  return (
    <div className="min-h-screen w-full bg-[#131316] text-white">
      <Navbar />

      <div className="w-full flex justify-center">
        <main
          className="w-full max-w-4xl border-x-2 border-[#6A6B70] border-dashed min-h-screen pt-19 px-2 pb-10 
        sm:pb-20 sm:px-4 sm:pt-21
        md:px-8 md:pt-24"
        >
          <div className="w-full space-y-6">
            <TopicFilterBar
              tags={tagRows}
              activeSlug={activeTag?.slug ?? null}
              tagQueryInvalid={tagQueryInvalid}
            />

            {activeTag && !tagQueryInvalid && (
              <div className="flex flex-wrap items-baseline justify-between gap-2 px-1">
                <h2 className="text-lg font-bold text-white">
                  <span className="text-[#6A6B70] font-semibold text-sm uppercase tracking-wider mr-2">
                    Topic
                  </span>
                  {activeTag.name}
                </h2>
                <p className="text-sm text-[#6A6B70]">
                  {posts.length} post{posts.length === 1 ? "" : "s"}
                </p>
              </div>
            )}

            {posts && posts.length > 0 ? (
              posts.map((post: Post) => (
                <BlogCard key={post.id} post={post} />
              ))
            ) : (
              <div className="text-center text-gray-500 mt-16 space-y-2">
                <p>
                  {activeTag && !tagQueryInvalid
                    ? "No published posts with this tag yet."
                    : "No posts found."}
                </p>
                <p className="text-sm text-[#6A6B70]">
                  {activeTag && !tagQueryInvalid
                    ? "Try another topic or view all posts."
                    : "Check back after the next ingest run."}
                </p>
                {activeTag && !tagQueryInvalid && (
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
            )}

            {posts && posts.length > 0 && (
              <p className="text-center text-sm text-gray-400 px-10 sm:pt-10 sm:pb-6">
                {activeTag && !tagQueryInvalid
                  ? "End of results for this topic."
                  : "That's all for now! Check back after the next update."}
              </p>
            )}
          </div>
        </main>
      </div>
    </div>
  );
}
