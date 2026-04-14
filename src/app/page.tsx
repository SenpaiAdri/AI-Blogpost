import Navbar from "@/components/Navbar";
import TopicFilterBar from "@/components/TopicFilterBar";
import PostFeed from "@/components/PostFeed";
import BackToTopButton from "@/components/BackToTopButton";
import {
  getPaginatedPosts,
  getTagBySlug,
  getTagsWithPostCounts,
} from "@/lib/posts";
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
  const tagRows = await getTagsWithPostCounts();

  const activeTag = rawTag ? await getTagBySlug(rawTag) : null;
  let tagQueryInvalid = false;
  const effectiveTagSlug = activeTag?.slug ?? null;

  if (rawTag) {
    if (!activeTag) {
      tagQueryInvalid = true;
    }
  }
  const initialPage = await getPaginatedPosts(
    0,
    10,
    tagQueryInvalid ? undefined : effectiveTagSlug ?? undefined
  );

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
            <PostFeed
              initialPosts={initialPage.posts}
              activeTagSlug={effectiveTagSlug}
              activeTagName={activeTag?.name ?? null}
              tagQueryInvalid={tagQueryInvalid}
              pageSize={10}
            />
          </div>
        </main>
      </div>
      <BackToTopButton />
    </div>
  );
}
