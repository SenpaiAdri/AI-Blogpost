import BlogCard from "@/components/BlogCard";
import Navbar from "@/components/Navbar";
import { supabase } from "@/lib/supabase";
import { Post, Tag } from "@/lib/types";

// Revalidate data every 120 seconds
// export const revalidate = 120;

export default async function Home() {
  // Fetch posts from Supabase including tags
  const { data: rawPosts, error } = await supabase
    .from("posts")
    .select(`
      *,
      post_tags (
        tags (
          *
        )
      )
    `)
    .eq("is_published", true)
    .order("published_at", { ascending: false });

  if (error) {
    console.error("Error fetching posts:", error);
    // } else {
    //   console.log("Fetched posts:", rawPosts?.length, "posts");
    //   console.log("Raw Posts Data:", JSON.stringify(rawPosts, null, 2));
  }

  // Move fetched data to the Post interface
  const posts: Post[] = (rawPosts || []).map((post: any) => {
    const tags = post.post_tags?.map((pt: any) => pt.tags as Tag) || [];
    // console.log(`Post: ${post.title}, \nTags:`, tags);
    return {
      ...post,
      tags
    };
  });

  return (
    <div className="min-h-screen w-full bg-[#131316] text-white">
      <Navbar />

      {/* Main Layout Container */}
      <div className="w-full flex justify-center">
        <main className="w-full max-w-4xl border-x-2 border-[#6A6B70] border-dashed min-h-screen pt-24 px-4 sm:px-8 pb-20">
          <div className="w-full space-y-6">
            {posts && posts.length > 0 ? (
              posts.map((post: Post) => (
                <BlogCard key={post.id} post={post} />
              ))
            ) : (
              <div className="text-center text-gray-500 mt-20">
                <p>No posts found.</p>
                <p className="text-sm">Wait for the AI to publish something tomorrow!</p>
              </div>
            )}

            {posts && posts.length > 0 && (
              <p className="text-center text-gray-400 pt-10 pb-10">
                That's all for now! Check back tomorrow for more posts.
              </p>
            )}
          </div>
        </main>
      </div>
    </div>
  );
}
