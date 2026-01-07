import Navbar from "@/components/Navbar";
import Tags from "@/components/Tags";
import { supabase } from "@/lib/supabase";
import { Post, Tag } from "@/lib/types";
import { notFound } from "next/navigation";
import Link from "next/link";
import Markdown from "react-markdown";

// Revalidate data every 120 seconds
export const revalidate = 120;

// Optional: Generate static paths for better performance at build time
export async function generateStaticParams() {
  const { data: posts } = await supabase.from("posts").select("slug");
  return posts?.map(({ slug }) => ({ slug })) || [];
}

export default async function BlogPost({ params }: { params: Promise<{ slug: string }> }) {
  // Await params in newer Next.js versions
  const { slug } = await params;

  // Fetch the specific post by slug
  const { data: postData, error } = await supabase
    .from("posts")
    .select(`
      *,
      post_tags (
        tags (
          *
        )
      )
    `)
    .eq("slug", slug)
    .single();

  if (error || !postData) {
    notFound();
  }

  const post: Post = {
    ...postData,
    tags: postData.post_tags?.map((pt: any) => pt.tags as Tag) || []
  };

  return (
    <div className="min-h-screen w-full bg-[#131316] text-white">
      <Navbar />

      <div className="w-full flex justify-center">
        <main className="w-full max-w-4xl border-x-2 border-[#6A6B70] border-dashed min-h-screen pt-24 px-4 sm:px-8 pb-20">
          <div className="max-w-3xl mx-auto space-y-5">
            {/* Back Button
            <Link
              href="/"
              className="text-gray-400 hover:text-white transition-colors text-sm flex items-center gap-2"
            >
              <span>&lt;</span> Back to posts
            </Link> */}

            {/* Header */}
            <header className="space-y-4">
              <h1 className="text-3xl sm:text-4xl md:text-5xl font-bold leading-tight">
                {post.title}
              </h1>

              <div className="flex flex-wrap gap-4 items-center justify-between">
                <Tags tags={post.tags || []} />
                <span className="text-gray-400 text-sm">
                  {new Date(post.published_at || "").toLocaleDateString('en-US', {
                    year: 'numeric',
                    month: 'long',
                    day: 'numeric'
                  })}
                </span>
              </div>
            </header>

            {/* TL;DR Section */}
            {post.tldr && post.tldr.length > 0 && (
              <div className="px-4">
                <p className="text-xs sm:text-sm font-bold text-[#808080] my-2">TL;DR</p>
                <ul className="space-y-2">
                  {post.tldr.map((item: string | any, index: number) => (
                    <li key={index} className="flex items-start text-white text-sm sm:text-base">
                      <span className="mr-2">•</span>
                      <span>{typeof item === 'string' ? item : item.name}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Main Content */}
            <article className="max-w-none text-white leading-relaxed space-y-4 mt-10">
              <Markdown components={{
                p: ({ children }) => <p className="text-white">{children}</p>,
                h1: ({ children }) => <h1 className="text-3xl font-bold text-white">{children}</h1>,
                h2: ({ children }) => <h2 className="text-2xl font-bold text-white">{children}</h2>,
                h3: ({ children }) => <h3 className="text-xl font-bold text-white">{children}</h3>,
                h4: ({ children }) => <h4 className="text-lg font-bold text-white">{children}</h4>,
              }}>{post.content || ""}</Markdown>
            </article>

            {/* Sources Footer */}
            {post.source_url && post.source_url.length > 0 && (
              <div className="pt-8 border-t border-[#393A41] mt-12">
                <h3 className="text-sm font-bold text-gray-400 mb-3">Sources</h3>
                <div className="flex flex-wrap gap-3">
                  {post.source_url.map((source: any, i) => {
                    const url = typeof source === 'string' ? null : source.url;
                    const name = typeof source === 'string' ? source : (source.name || source.url);
                    return url ? (
                      <a
                        key={i}
                        href={url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-400 hover:text-blue-300 text-sm bg-[#1C1C21] px-3 py-1.5 rounded-md transition-colors"
                      >
                        {name} ↗
                      </a>
                    ) : (
                      <span key={i} className="text-gray-500 text-sm px-3 py-1.5 border border-[#393A41] rounded-md">{name}</span>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  );
}
