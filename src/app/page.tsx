import BlogCard from "@/components/BlogCard";
import Navbar from "@/components/Navbar";
import { getPosts } from "@/lib/posts";
import { Post } from "@/lib/types";

// Revalidate data every 120 seconds
export const revalidate = 120;

export default async function Home() {
  const posts: Post[] = await getPosts();

  return (
    <div className="min-h-screen w-full bg-[#131316] text-white">
      <Navbar />

      {/* Main Layout Container */}
      <div className="w-full flex justify-center">
        <main className="w-full max-w-4xl border-x-2 border-[#6A6B70] border-dashed min-h-screen pt-19 px-2 pb-10 
        sm:pb-20 sm:px-4 sm:pt-21
        md:px-8 md:pt-24">
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
              <p className="text-center text-sm text-gray-400 px-10 sm:pt-10 sm:pb-10">
                That&apos;s all for now! Check back tomorrow for more posts.
              </p>
            )}
          </div>
        </main>
      </div>
    </div>
  );
}
