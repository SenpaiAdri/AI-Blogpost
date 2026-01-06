import BlogCard from "@/components/BlogCard";
import Navbar from "@/components/Navbar";
import { supabase } from "@/lib/supabase";
import { Post, Tag } from "@/lib/types";

// Revalidate data every 120 seconds
export const revalidate = 120;

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
  } else {
    console.log("Raw Posts Data:", JSON.stringify(rawPosts, null, 2));
  }

  // Transform the data to match our Post interface
  const posts: Post[] = (rawPosts || []).map((post: any) => {
    const tags = post.post_tags?.map((pt: any) => pt.tags) || [];
    // console.log(`Post: ${post.title}, Tags:`, tags);
    return {
      ...post,
      tags
    };
  });

  return (
    <div className="h-screen w-full bg-[#131316]">
      <Navbar />
      <div className="h-full w-full flex flex-row items-center justify-center">
        {/* Left Side */}
        <div className="h-full hidden sm:block sm:flex-[.25] md:flex-[.5] lg:flex-1"></div>
        {/* Main Content */}
        <div className="h-full flex-2 border border-[#6A6B70] border-dashed border-b-0 border-t-0 border-x-2">
          <main className="h-full w-full flex flex-col items-center pt-24 px-4 overflow-y-auto no-scrollbar">
                        
            <div className="w-full space-y-6 pb-20">
              {posts && posts.length > 0 ? (
                posts.map((post: Post) => (
                  <BlogCard key={post.id} post={post} />
                ))
              ) : (
                <div className="text-center text-gray-500 mt-10">
                  <p>No posts found.</p>
                  <p className="text-sm">Wait for the AI to publish something!</p>
                </div>
              )}
            </div>
          </main>
        </div>
        {/* Right Side */}
        <div className="h-full hidden sm:block sm:flex-[.25] md:flex-[.5] lg:flex-1"></div>
      </div>
    </div>
  );
}
